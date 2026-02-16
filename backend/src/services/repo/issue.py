from fastapi import HTTPException

from github import Github, Auth

def create_github_issue(token: str, repo_name: str, title: str, body: str) -> dict:
    """


    """

    # Authenticate GitHub token
    github_auth = Auth.Token(token)

    with Github(auth=github_auth) as github_client:

        # Connect to GitHub repo
        repo = github_client.get_repo(repo_name)

        # Check user permission to create issue
        user = github_client.get_user()
        permission = repo.get_collaborator_permission(user.login)

        if permission not in ["write", "admin", "maintain"]:
            raise HTTPException(
                status_code=403,
                detail=f"Not permitted to create issues. Current permission: {permission}"
            )
        
        # Create issue
        issue = repo.create_issue(
            title=title,
            body=body
        )

        return {
            "number": issue.number,
            "url": issue.html_url,
            "title": issue.title,
            "created_at": issue.created_at.isoformat()
        }