import requests
from fastapi import APIRouter, HTTPException

from core.config import settings
from schemas.request.repo.create_issue import CreateIssueRequest

router = APIRouter(prefix="/repo", tags=["repo"])

@router.get("/repo-preview")
async def create_issue():
    """
    Fetches repository metadata and file tree from GitHub for the sandbox repo.

    Proxies the GitHub API requests server-side so the GitHub token is never
    exposed to the frontend bundle. Returns repo metadata (name, description,
    stars, language) and the full recursive file tree for display in the
    repo viewer.

    Returns:
        Dictionary containing:
        - repo: Full GitHub repository metadata object
        - tree: Flat list of file and directory tree items with paths and types

    Raises:
    HTTPException: If either the repo metadata or tree request fails.
    """

    github_token = settings.GITHUB_TOKEN.get_secret_value()
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json"
    }
    
    repo_response = requests.get("https://api.github.com/repos/chihaos1/jira_clone", headers=headers)
    tree_response = requests.get("https://api.github.com/repos/chihaos1/jira_clone/git/trees/master?recursive=1", headers=headers)

    if not repo_response.ok or not tree_response.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch repo data")
    
    return {
        "repo": repo_response.json(),
        "tree": tree_response.json().get("tree", [])
    }