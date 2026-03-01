import requests
from celery import Task

from celery_app import celery_app
from .code import process_file_group
from .state import (
    get_workflow_state,
    get_ready_groups,
    update_group_status,
    update_workflow_state
)

SANDBOX_URL = "http://localhost:5001"

def _merge_all_files(state: dict) -> list:
    """Merge all generated files from all groups."""

    all_files = []
    for group_state in state["groups"].values():
        if group_state.get("result") and group_state['result'].get('files'):
            all_files.extend(group_state['result']['files'])
    return all_files

def _send_to_sandbox(workflow_id: str, all_files: list, state: dict) -> None:
    """Send merged files to sandbox for testing and update workflow status."""

    try:
        payload = {
            "files": all_files,
            "commands": ["npm install", "npm run build", "npm test"],
            "workflow_id": workflow_id,
            "repo_name": state['repo_name'],
            "github_token": state['github_token'],
            "runtime": "node"
        }
        
        print(f"Sending {len(all_files)} files to sandbox...")
        
        response = requests.post(
            f"{SANDBOX_URL}/execute",
            json=payload,
            timeout=600
        )
        
        sandbox_result = response.json()
        print(f"Sandbox result: success={sandbox_result.get('success')}")

        # Update workflow with sandbox results
        final_status = 'completed' if sandbox_result.get('success') else 'failed'
        update_workflow_state(
            workflow_id=workflow_id,
            status=final_status,
            sandbox_result=sandbox_result
        )
        
        print(f"Workflow marked as {final_status}")
        
    except Exception as e:
        print(f"Sandbox error: {e}")
        update_workflow_state(
            workflow_id=workflow_id,
            status='failed',
            sandbox_result={'error': str(e)}
        )

def _dispatch_coder_groups(state: dict, workflow_id: str, ready_groups: list) -> None:
    """Dispatch ready Coder groups to workers."""

    execution_plan = state['execution_plan']
    understanding = execution_plan['understanding']
    
    for group_id in ready_groups:
        file_group = next(
            (group for group in execution_plan['file_groups'] if group['group_id'] == group_id),
            None
        )
    
        if not file_group:
            print(f"Group {group_id} not found")
            continue
        
        task = process_file_group.apply_async(
            args=[
                file_group,
                understanding,
                state["issue_description"],
                state["repo_name"],
                state["github_token"]
            ],
            link=mark_complete.s(workflow_id, group_id)
        )

        update_group_status(
            workflow_id=workflow_id,
            group_id=group_id,
            status="running",
            task_id=task.id
        )

        print(f"Dispatched {group_id} (task: {task.id})")

@celery_app.task(name="orchestrate", bind=True)
def orchestrate_workflow(self: Task, workflow_id: str) -> None:
    """
    Coordinates file group execution.
    
    Steps:
    1. Reads workflow state from Redis
    2. Finds groups whose dependencies are satisfied
    3. Dispatches those groups to workers
    4. Sets up callbacks to retrigger itself when groups complete
    5. Merge and send generated code to sandbox when all groups are done
    """

    state = get_workflow_state(workflow_id)

    # ===== 1. Check workflow state =====
    if not state:
        print(f"Workflow {workflow_id} not found in Redis")
        return
    
    if state['status'] in ['completed', 'failed']:
        print(f"Workflow {workflow_id} already {state['status']}")
        return
    
    # ===== 2. Check if all groups are done =====
    all_done = all(
        group["status"] == "completed"
        for group in state["groups"].values()
    )

    if all_done:

        print(f"All groups completed - merging files and sending to sandbox")

        # If coding groups are done, send to sandbox for review
        all_files = _merge_all_files(state)
        _send_to_sandbox(workflow_id, all_files, state)
        return 
        
    # ===== 3. Check if any groups failed =====
    any_failed = any(
        group['status'] == 'failed'
        for group in state['groups'].values()
    )
    
    if any_failed:
        print(f"Groups failed - workflow failed")
        update_workflow_state(workflow_id, status='failed', sandbox_result=None)
        return
    
    # ===== 4. Find ready file groups to dispatch =====
    ready_groups = get_ready_groups(workflow_id)

    if not ready_groups:
        print(f"No groups ready yet for workflow {workflow_id}")
        return
    
    print(f"Dispatching {len(ready_groups)} groups: {ready_groups}")

    _dispatch_coder_groups(state, workflow_id, ready_groups)
    
    print(f"Waiting for callbacks...")

@celery_app.task(name="mark_complete", bind=True)
def mark_complete(self: Task, result: dict, workflow_id: str, group_id: str) -> None:
    """
    Callback triggered when a file group completes.
    
    Steps:
    1. Updates Redis with the result
    2. Triggers the brain to check for newly ready groups
    """

    print(f"Group completed: {group_id} (workflow: {workflow_id})")

    # Determine status based on result
    status = "completed" if result.get("status") == "success" else "failed"

    update_group_status(
        workflow_id=workflow_id,
        group_id=group_id,
        status=status,
        result=result
    )

    print(f"Triggering orchestrator to check for next groups...")
    orchestrate_workflow.delay(workflow_id)