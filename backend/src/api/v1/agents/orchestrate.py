import logging
import time
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.agents.orchestrate import OrchestrateRequest
from schemas.response.agents.orchestrate import OrchestrateResponse
from services.graph.state import create_initial_state
from services.graph.builder import build_graph
from services.observability.posthog_client import posthog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest):
    """
    Start AutoDev ReAct workflow.
    
    Flow:
    1. Create initial state from request
    2. Build graph with tools
    3. Invoke graph
    4. Return result
    """

    try:

        session_id = str(uuid.uuid4())
        logger.info(f"Starting AutoDev workflow: session={session_id}, repo={request.repo_name}")

        # 1. Create initial state
        state = create_initial_state(
            issue_id=session_id,  # Or use actual GitHub issue ID if available
            issue_description=request.query,
            repo_name=request.repo_name,
            branch_name="main",  # Or from request
            session_id=session_id,
            llm_model="claude-sonnet-4-20250514"
        )

        # 2. Build graph with GitHub token
        graph = build_graph(
            github_token=request.github_token.get_secret_value(),
            enable_checkpointing=True
        )

        logger.info(f"Graph built for session {session_id}")

        # ========== TRACK: Workflow Started ========== 
        posthog.capture(
            distinct_id=session_id,
            event="agent_run_started",
            properties={
                "repo_name": request.repo_name,
                "issue_id": "TEST", #request.issue_id, #NEED TO TRIGGER WORkLDOAD FROM GITHUB ISSUE
                "issue_description": "TEST", #request.issue_description, #NEED TO TRIGGER WORkLDOAD FROM GITHUB ISSUE
                "timestamp": datetime.now().isoformat()
            }
        )
        # ========== END TRACK ==========

        # 3. Run graph
        start_time = time.time()
        config = {"configurable": {"thread_id": session_id}}
        result = graph.invoke(state, config)

        logger.info(
            f"Workflow completed: session={session_id}, "
            f"final_step={result['current_step']}, "
            f"messages={len(result['messages'])}",
        )
        duration = int((time.time() - start_time))
        
        # ========== TRACK: Workflow Completed ========== 
        posthog.capture(
            distinct_id=session_id,
            event="agent_run_completed",
            properties={
                'success': True,
                'total_cost_usd': result.get('estimated_cost_usd', 0),
                'total_duration_s': duration,
                'pr_url': result.get('pr_url'),
                "timestamp": datetime.now().isoformat()
            }
        )
        # ========== END TRACK ==========

        return OrchestrateResponse(
            workflow_id=session_id,
            status=result["current_step"],
            pr_url=result.get("pr_url"),
            files_modified=len(result.get("files_to_modify", [])),
            cost_usd=result.get("estimated_cost_usd", 0.0)
        )

    except GithubException as e:
        if e.status == 401:
            raise HTTPException(status_code=401, detail="Invalid Github token")
        elif e.status == 404:
            raise HTTPException(status_code=404, detail=f"Repository {request.repo_name} was not found or no permission to access")
        else:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
    except Exception as e:
        
        # ========== TRACK: Workflow Failed ========== ↓
        posthog.capture(
            distinct_id=session_id,
            event='agent_run_failed',
            properties={
                'success': False,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'failure_phase': result.get('current_step'),
                'timestamp': datetime.now().isoformat()
            }
        )
        # ========== END TRACK ==========
        
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
