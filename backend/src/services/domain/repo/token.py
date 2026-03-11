from github import Github, Auth

def get_github_repo_info(token: str, repo_name: str) -> dict:
    """
    Validate GitHub token and confirm repo access.
    
    Steps:
    1. Authenticate the GitHub token.
    2. Verify access to the specified repository.
    3. Retrieve repository metadata (URL, file count).
    4. Return the connection status to the frontend.

    Args:
        token (str): The GitHub Personal Access Token (PAT).
        repo_name (str): The full name of the repository (e.g., 'owner/repo').

    Returns:
        dict: A dictionary containing:
            - "html_url" (str): The direct browser link to the repository.
            - "file_count" (int): Total number of files (blobs) in the default branch.
            - "full_name" (str): The formal owner/repo name.

    """
    # Authenticate GitHub token
    github_auth = Auth.Token(token)

    with Github(auth=github_auth) as github_client:

        # Connect to GitHub repo
        repo = github_client.get_repo(repo_name)

        # Get file count
        tree = repo.get_git_tree(sha=repo.default_branch, recursive=True)
        file_count = sum(1 for item in tree.tree if item.type == "blob")

        return {
            "html_url": repo.html_url,
            "file_count": file_count,
            "full_name": repo.full_name
        }