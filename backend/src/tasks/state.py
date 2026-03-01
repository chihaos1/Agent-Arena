import json
import redis
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.config import settings

redis_client = redis.Redis.from_url(
    settings.CELERY_BROKER_URL,
    decode_responses=True
)

def create_workflow_state(
    workflow_id: str,
    execution_plan: dict,
    issue_description: str,
    repo_name: str,
    github_token: str
) -> None:
    """Initialize workflow state in Redis"""

    groups = {}
    for group in execution_plan["file_groups"]:
        groups[group["group_id"]] = {
            "status": "pending",
            "task_id": None,
            "started_at": None,
            "completed_at": None,
            "result": None
        }
    
    state = {
        "workflow_id": workflow_id,
        "status": "running",
        "sandbox_result": "",
        "execution_plan": execution_plan,
        "issue_description": issue_description,
        "repo_name": repo_name,
        "github_token": github_token,
        "groups": groups,
        "created_at": datetime.now(timezone.utc).timestamp(),
        "updated_at": datetime.now(timezone.utc).timestamp()
    }
    print(f"REDIS STATE {state}")
    key = f"workflow:{workflow_id}"
    redis_client.set(key, json.dumps(state))
    redis_client.expire(key, 86400)

def get_workflow_state(workflow_id: str) -> Optional[Dict]:
    """Get workflow state from Redis"""

    key = f"workflow:{workflow_id}"
    data = redis_client.get(key)

    if data:
        return json.loads(data)
    return None

def update_workflow_state(
    workflow_id: str,
    status: str,
    sandbox_result: str
) -> None:
    """Update the workflow's status"""

    state = get_workflow_state(workflow_id)
    if not state:
        return 
    
    state["status"] = status
    state["sandbox_result"] = sandbox_result

    key = f"workflow:{workflow_id}"
    redis_client.set(key, json.dumps(state))

def update_group_status(
    workflow_id: str,
    group_id: str,
    status: str,
    task_id: Optional[str] = None,
    result: Optional[Dict] = None
) -> None:
    """Update a group's status in the workflow"""

    state = get_workflow_state(workflow_id)
    if not state:
        return 

    if status == "running":
        state["groups"][group_id]["status"] = "running"
        state['groups'][group_id]['task_id'] = task_id
        state['groups'][group_id]['started_at'] = datetime.now(timezone.utc).timestamp()

    elif status in ["completed", "failed"]:
        state['groups'][group_id]['status'] = status
        state['groups'][group_id]['completed_at'] = datetime.now(timezone.utc).timestamp()
        state['groups'][group_id]['result'] = result
    
    state["updated_at"] = datetime.now(timezone.utc).timestamp()

    key = f"workflow:{workflow_id}"
    redis_client.set(key, json.dumps(state))

def get_ready_groups(workflow_id: str) -> List:
    """Get groups that are ready to start (dependencies satisfied)"""

    state = get_workflow_state(workflow_id)
    if not state:
        return []
    
    execution_plan = state['execution_plan']
    groups = state['groups']
    ready = []

    for group in execution_plan["file_groups"]:
        group_id = group["group_id"]

        # Skip if already running or completed
        if groups[group_id]["status"] != "pending":
            continue

        # Check if all dependencies are completed
        dependencies = group.get("dependencies", [])
        dependencies_satisfied = all(
            groups.get(dependency, {}).get("status") == "completed" # Check if group was completed
            for dependency in dependencies # Dependency is group name
        )

        if dependencies_satisfied:
            ready.append(group_id)
    
    return ready