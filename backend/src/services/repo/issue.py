from fastapi import HTTPException

from github import Github, Auth

def create_github_issue(token: str, repo_name: str, title: str, body: str) -> dict:
    """
    Verifies that the authenticated user has sufficient permissions 
    (write, admin, or maintainer) before attempting to create the issue.

    Args:
        token: A GitHub Personal Access Token (PAT) for authentication.
        repo_name: The full name of the repository (e.g., "owner/repo").
        title: The title of the issue to be created.
        body: The markdown description/content of the issue.

    Returns:
        dict: A dictionary containing the issue metadata:
            - number (int): The GitHub issue number.
            - url (str): The web URL to view the issue.
            - title (str): The issue title.
            - created_at (str): ISO formatted timestamp of creation.

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