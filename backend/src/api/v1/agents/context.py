from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.agents.context import SearchContextRequest
from schemas.response.agents.context import ContextAssemblerResponse
from services.domain.context.assembler import ContextAgent

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/build-context", response_model=ContextAssemblerResponse)
async def build_context(request: SearchContextRequest):
    """
    Orchestrates the retrieval and parsing of repository context for a given query.
    Will first fetch relevant files from Pinecone then conduct code fetching and AST parsing.

    Args:
    * request (SearchContextRequest): The validated request body.
    * Attributes:
        * query (str): The natural language issue or request to search against.
        * repo_name (str): Full name of the repository (e.g., 'owner/repo').
        * github_token (SecretStr): A secure GitHub Personal Access Token.

    Returns:
    * ContextAssemblerResponse: The structured payload containing the gathered context.
    * Attributes:
        * issue (dict): Contains the original query for reference.
        * repo_context (dict): Metadata including the repository name and language stack.
        * files (list): A collection of relevant file objects, each containing a summary, 
          top-level signatures, and import dependencies.
    """

    try: 
        
        assembler = ContextAgent(
            github_token=request.github_token.get_secret_value()
        )

        context = assembler.assemble_context(
            query=request.query, 
            repo_name=request.repo_name
        )

        return ContextAssemblerResponse(
            issue=context["issue"],
            repo_context=context["repo_context"],
            files=context["files"]
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