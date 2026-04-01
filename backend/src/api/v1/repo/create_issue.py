import requests
from fastapi import APIRouter, HTTPException

from core.config import settings
from schemas.request.repo.create_issue import CreateIssueRequest

router = APIRouter(prefix="/repo", tags=["repo"])

@router.post("/create-issue")
async def create_issue(request: CreateIssueRequest):
    """
    Creates a GitHub issue on the specified repository.

    Uses the server-side GitHub token from environment variables to authenticate,
    keeping credentials off the frontend. Returns the created issue number for
    use in the Arena run pipeline.

    Args:
        request: Repository name, issue title, and issue body.

    Returns:
        Dictionary containing the created issue number e.g. {"issue_number": 42}

    Raises:
        HTTPException: If the GitHub API returns a non-2xx response.
    """
    
    github_token = settings.GITHUB_TOKEN.get_secret_value()
    response = requests.post(
        f"https://api.github.com/repos/{request.repo_name}/issues",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Content-Type": "application/json"
        },
        json={"title": request.title, "body": request.body}
    )

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail="Failed to create GitHub issue")
    
    data = response.json()
    return { "issue_number": data["number"] }