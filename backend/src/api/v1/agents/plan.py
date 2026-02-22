from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.agents.plan import PlanRequest
from schemas.response.agents.plan import PlanResponse
from services.agents.plan import PlannerAgent


router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/plan-execution", response_model=PlanResponse)
async def build_context(request: PlanRequest):
    """
    """

    try: 

        planner = PlannerAgent()
        planner.create_plan()
        

        return PlanResponse(
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