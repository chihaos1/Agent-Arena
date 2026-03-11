from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.agents.plan import ExecutionPlanRequest
from schemas.response.agents.plan import ExecutionPlanResponse
from services.domain.plan.planner import PlannerAgent

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/plan-execution", response_model=ExecutionPlanResponse)
async def plan_execution(request: ExecutionPlanRequest):
    """
    Generates and validates of a multi-step repository edit strategy.
    
    This phase transitions from raw repository context to a structured roadmap, utilizing 
    a Planner Agent to group related files and establish a dependency-aware execution order.

    Args:
    * request (ExecutionPlanRequest): The validated request body.
    * Attributes:
        * context (ContextAssemblerResponse): The structured context gathered from 
          Pinecone and AST parsing.
        * repo_name (str): Full name of the repository (e.g., 'owner/repo').
        * github_token (SecretStr): A secure GitHub Personal Access Token.

    Returns:
    * ExecutionPlanResponse: The structured roadmap for the Coder Agents.
    * Attributes:
        * understanding (str): The high-level technical strategy synthesized by the AI.
        * file_groups (list): A collection of FileGroup objects, each defining a 
          specific set of files to be edited together.
        * execution_order (list): A sequence of group IDs ensuring base dependencies 
          are modified before their dependents.
    """

    try: 
        
        # Create and review execution plan with Planner
        planner = PlannerAgent()

        execution_plan = planner.create_plan()
        
        return ExecutionPlanResponse(
            understanding=execution_plan["understanding"],
            file_groups=execution_plan["file_groups"],
            execution_order=execution_plan["execution_order"]
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