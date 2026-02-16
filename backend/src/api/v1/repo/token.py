from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.token import ValidateTokenRequest
from schemas.response.token import ValidateTokenResponse
from services.repo.token import get_github_repo_info

router = APIRouter(prefix="/repo", tags=["repo"])

@router.post("/validate-token", response_model=ValidateTokenResponse)
async def validate_token(request: ValidateTokenRequest):
    """
    Validate GitHub token and confirm repo access.

    Returns:
    * ValidateTokenResponse: Contains the result of the validation.
    * Attributes:
        * success (bool): True if token is valid and repo is accessible; False otherwise.
        * repo_name (str): Name of the repository provided.
        * repo_url (str): GitHub URL of the repository.
        * total_files (int): Number of files in the repository.
        * message (str): Human-readable message describing the validation result.
    """

    try: 

        # Get repo info using service function
        repo_data = get_github_repo_info(
            request.github_token.get_secret_value(),
            request.repo_name
        )

        return ValidateTokenResponse(
            success=True,
            repo_name=request.repo_name,
            repo_url=repo_data["html_url"],
            total_files=repo_data["file_count"],
            message=f"Successfuly connected to {repo_data['full_name']}"
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