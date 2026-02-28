from celery import Task

from celery_app import celery_app
from .code import process_file_group
from .state import (
    get_workflow_state,
    get_ready_groups,
    update_group_status
)

@celery_app.task(name="orchestrate", bind=True)
def orchestrate_workflow(self: Task, workflow_id: str) -> None:
    """
    Coordinates file group execution.
    
    Steps:
    1. Reads workflow state from Redis
    2. Finds groups whose dependencies are satisfied
    3. Dispatches those groups to workers
    4. Sets up callbacks to retrigger itself when groups complete
    5. Exits when all groups are done
    """

    state = get_workflow_state(workflow_id)

    # Check workflow state
    if not state:
        print(f"Workflow {workflow_id} not found in Redis")
        return
    
    if state['status'] in ['completed', 'failed']:
        print(f"Workflow {workflow_id} already {state['status']}")
        return
    
    # Find ready file groups
    ready_groups = get_ready_groups(workflow_id)

    if not ready_groups:
        print(f"No groups ready yet for workflow {workflow_id}")
        return
    
    print(f"Dispatching {len(ready_groups)} ready groups: {ready_groups}")

    # Get plan and understanding
    execution_plan = state['execution_plan']
    understanding = execution_plan['understanding'] 

    # Find the ready file group by ID
    for group_id in ready_groups:
        
        file_group = next(
            (group for group in execution_plan['file_groups'] if group['group_id'] == group_id),
            None
        )
    
        if not file_group:
            print(f"Group {group_id} not found in execution plan")
            continue
        
        # Dispatch file group to coder agent
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

    print(f"Orchestration done, waiting for callbacks...")

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