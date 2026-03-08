import json
import logging
import redis
import requests
from celery import Task
from core.config import settings

from celery_app import celery_app
from .code import process_file_group
from .state import (
    get_workflow_state,
    get_ready_groups,
    update_group_status,
    update_workflow_state
)
from .tool.create_pr import PullRequestGenerator

SANDBOX_URL = "http://localhost:5001"
logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    settings.CELERY_BROKER_URL,
    decode_responses=True
)

def _merge_all_files(state: dict) -> list:
    """Merge all generated files from all groups."""

    all_files = []
    for group_state in state["groups"].values():
        if group_state.get("result") and group_state['result'].get('files'):
            all_files.extend(group_state['result']['files'])

    logger.info("All files merged")
    return all_files

def _dispatch_coder_groups(state: dict, workflow_id: str, ready_groups: list) -> None:
    """Dispatch ready Coder groups to workers."""

    execution_plan = state['execution_plan']
    understanding = execution_plan['understanding']
    
    for group_id in ready_groups:
        file_group = next( #Get the ready file group
            (group for group in execution_plan['file_groups'] if group['group_id'] == group_id),
            None
        )
    
        if not file_group:
            logging.info(f"Group {group_id} not found")
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

        logger.info(f"Dispatched {group_id} (task: {task.id})")

def _send_to_sandbox(workflow_id: str, all_files: list, state: dict) -> None:
    """Send merged files to sandbox for testing and update workflow status."""

    try:
        
        # Aggregate the commands
        setup_cmds = state.get("setup_commands", [])
        test_cmds = state.get("test_commands", [])
        all_cmds = setup_cmds + test_cmds
        all_cmds_subshells = [f"({cmd})" for cmd in all_cmds]
        final_cmds = " && ".join(all_cmds_subshells)

        logger.info(f"Commands to run in Sandbox {all_cmds_subshells}")

        # Get the runtimes
        runtimes = state.get("runtimes", ["node"])
        logger.info(f"Runtime in Sandbox {runtimes}")

        payload = {
            "files": all_files,
            "commands": final_cmds,
            "workflow_id": workflow_id,
            "repo_name": state['repo_name'],
            "github_token": state['github_token'],
            "runtime": runtimes
        }
        
        logger.info(f"Sending {len(all_files)} files to sandbox...")
        
        response = requests.post(
            f"{SANDBOX_URL}/execute",
            json=payload,
            timeout=600
        )
        
        sandbox_result = response.json()
        logger.info(f"Sandbox result: success={sandbox_result.get('success')}")

        # Update workflow with sandbox results
        final_status = 'completed' if sandbox_result.get('success') else 'failed'
        update_workflow_state(
            workflow_id=workflow_id,
            status=final_status,
            sandbox_result=sandbox_result
        )

        # Generates PR based on final sandbox result
        if sandbox_result.get('success'):
            _create_pull_request(workflow_id, all_files, state, sandbox_result)
            logger.info("Creating GitHub PR")
        else:
            logger.info("Skipping PR creation - sandbox tests failed")
            return
        
        logger.info(f"Workflow marked as {final_status}")
        
    except Exception as e:
        logger.error(f"Sandbox error: {e}")
        update_workflow_state(
            workflow_id=workflow_id,
            status='failed',
            sandbox_result={'error': str(e)}
        )

def _create_pull_request(workflow_id: str, all_files: list, state: dict, sandbox_result: dict) -> None:
    """Create GitHub PR with generated code if sandbox tests passed"""

    try:
        pr_creator = PullRequestGenerator(state["github_token"])
        pr_result = pr_creator.create_pr(
            repo_name=state["repo_name"],
            files=all_files,
            workflow_id=workflow_id,
            issue_description=state['issue_description'],
            sandbox_result=sandbox_result
        )

        if pr_result.get("success"):
            logger.info(f"PR created: {pr_result['pr_url']}")

            state['pr_url'] = pr_result['pr_url']
            state['pr_number'] = pr_result['pr_number']
            redis_client.set(f"workflow:{workflow_id}", json.dumps(state))
        else:
            logger.error(f"PR creation failed: {pr_result.get('error')}")

    except Exception as e:
        logger.error(f"Exception during PR creation: {e}", exc_info=True)


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
        logger.warning(f"Workflow {workflow_id} not found in Redis")
        return
    
    if state['status'] in ['completed', 'failed']:
        logger.warning(f"Workflow {workflow_id} already {state['status']}")
        return
    
    # ===== 2. Check if all groups are done =====
    all_done = all(
        group["status"] == "completed"
        for group in state["groups"].values()
    )

    if all_done:

        logger.info(f"All groups completed - merging files and sending to sandbox")

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
        logger.warning(f"Groups failed - workflow failed")
        update_workflow_state(workflow_id, status='failed')
        return
    
    # ===== 4. Find ready file groups to dispatch =====
    ready_groups = get_ready_groups(workflow_id)

    if not ready_groups:
        logger.warning(f"No groups ready yet for workflow {workflow_id}")
        return
    
    logger.info(f"Dispatching {len(ready_groups)} groups: {ready_groups}")

    _dispatch_coder_groups(state, workflow_id, ready_groups)
    
    logger.info(f"Waiting for callbacks...")

@celery_app.task(name="mark_complete", bind=True)
def mark_complete(self: Task, result: dict, workflow_id: str, group_id: str) -> None:
    """
    Callback triggered when a file group completes.
    
    Steps:
    1. Updates Redis with the result
    2. Triggers the brain to check for newly ready groups
    """

    logger.info(f"Group completed: {group_id} (workflow: {workflow_id})")

    # Determine status based on result
    status = "completed" if result.get("status") == "success" else "failed"

    update_group_status(
        workflow_id=workflow_id,
        group_id=group_id,
        status=status,
        result=result
    )

    logger.info(f"Triggering orchestrator to check for next groups...")
    orchestrate_workflow.delay(workflow_id)