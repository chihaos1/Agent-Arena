from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.agents.context import SearchContextRequest
from schemas.response.agents.context import SearchContextResponse
from services.agents.context import ContextAssembler

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/build-context", response_model=SearchContextResponse)
async def build_context(request: SearchContextRequest):
    """

    """

    try: 
        
        assembler = ContextAssembler(
            github_token=request.github_token.get_secret_value()
        )

        assembler.assemble_context(
            query=request.query, 
            repo_name=request.repo_name
        )


        
        

        return SearchContextResponse(
            query=request.query,
            # relevant_files=request.repo_name,
            relevant_files=[""]
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