from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.agents.orchestrate import OrchestrateRequest
from schemas.response.agents.orchestrate import OrchestrateResponse
from services.agents.context import ContextAssembler
from services.agents.plan import PlannerAgent

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/orchestrate", response_model=OrchestrateResponse)
async def build_context(request: OrchestrateRequest):
    """
    """

    try: 
        
        # Organize the context for the Planner
        assembler = ContextAssembler(
            github_token=request.github_token.get_secret_value()
        )

        context = assembler.assemble_context(
            query=request.query, 
            repo_name=request.repo_name
        )

        print(context)

        # Create and review execution plan with Planner
        planner = PlannerAgent()
        planner.create_plan(context)


        return OrchestrateResponse(
            query="test"
        )

    except GithubException as e:
        if e.status == 401:
            raise HTTPException(status_code=401, detail="Invalid Github token")
        elif e.status == 404:
            raise HTTPException(status_code=404, detail=f"Repository {request.repo_name} was not found or no permission to access")
        else:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")