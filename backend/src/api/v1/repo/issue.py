from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.repo.issue import CreateIssueRequest
from schemas.response.repo.issue import CreateIssueResponse
from services.repo.issue import create_github_issue

router = APIRouter(prefix="/repo", tags=["repo"])

@router.post("/create-issue", response_model=CreateIssueResponse)
async def create_issue(request: CreateIssueRequest):
    """
    Authenticate with GitHub and create a new issue in the specified repository.

    Args:
    * request (CreateIssueRequest): The validated request body.
    * Attributes:
        * github_token (SecretStr): A valid GitHub Personal Access Token.
        * repo_name (str): Full name of the repository (e.g., 'owner/repo').
        * issue_title (str): Title of the issue to be created.
        * issue_description (str): Detailed content for the issue body.

    Returns:
    * CreateIssueResponse: Contains the detailed result of the issue creation.
    * Attributes:
        * success (bool): True if the issue was successfully created; False otherwise.
        * issue_number (int): The unique identifier assigned by GitHub to the new issue.
        * issue_url (str): The direct HTML link to the newly created issue.
        * issue_title (str): The title of the issue as confirmed by the API.
        * created_at (str): ISO 8601 formatted timestamp of the creation.
        * message (str): Human-readable confirmation including the repository name.
    """

    try: 

        issue_data = create_github_issue(
            request.github_token.get_secret_value(),
            request.repo_name,
            request.issue_title,
            request.issue_description
        )

        return CreateIssueResponse(
            success=True,
            issue_number=issue_data["number"],
            issue_url=issue_data["url"],
            issue_title=issue_data["title"],
            created_at=issue_data["created_at"],
            message=f"Issue number {issue_data["number"]} created at {request.repo_name}"
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