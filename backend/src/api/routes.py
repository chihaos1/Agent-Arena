from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from github import Github, Auth, GithubException

from models.validate_token import ValidateTokenResponse, ValidateTokenRequest

router = APIRouter()

@router.post("/repo/validate-token", response_model=ValidateTokenResponse)
async def validate_token(request: ValidateTokenRequest):
    """
    Validate GitHub token and confirm repo access.
    
    Steps:
    1. Validate token works
    2. Check repo access
    3. Get repo info
    4. Return details to frontend
    """

    try: 

        # Authenticate GitHub token
        github_auth = Auth.Token(request.github_token)
        github_client = Github(auth=github_auth)

        # Connect to GitHub repo
        repo = github_client.get_repo(request.repo_name)

        # Get file count
        tree = repo.get_git_tree(sha=repo.default_branch, recursive=True)
        file_count = sum(1 for item in tree.tree if item.type == "blob")

        return ValidateTokenResponse(
            success=True,
            repo_name=request.repo_name,
            repo_url=repo.html_url,
            total_files=file_count,
            message=f"successfuly connected to {repo.full_name}"
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
    
    finally:
        github_client.close()