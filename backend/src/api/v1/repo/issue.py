from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.issue import CreateIssueRequest
from schemas.response.issue import CreateIssueResponse
from services.repo.issue import create_github_issue

router = APIRouter(prefix="/repo", tags=["repo"])

@router.post("/create-issue", response_model=CreateIssueResponse)
async def create_issue(request: CreateIssueRequest):

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