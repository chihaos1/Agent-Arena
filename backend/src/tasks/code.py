from celery import Task
from github import Github

from celery_app import celery_app

from services.agents.code.agent import CoderAgent

@celery_app.task(name="process_file_group", bind=True, max_retries=3)
def process_file_group(
        self: Task,
        file_group: dict,
        understanding: str,
        issue_description: str,
        repo_name: str,
        github_token: str
    ) -> dict:
    """
    Process a single file group with the Coder Agent.
    
    This runs in a Celery worker (background process).
    
    Args:
        file_group_dict: FileGroup as dict (serializable)
        understanding: Overall strategy from planner
        issue_query: User's issue description
        repo_name: "owner/repo" format
        github_token: GitHub token
    
    Returns:
        Result dict with status, files, errors
    """

    try:

        # Reconstruct GitHub repo
        github = Github(github_token)
        repo = github.get_repo(repo_name)

        # Run Coder agent
        coder = CoderAgent()
        result = coder.run(
            file_group=file_group,
            understanding=understanding,
            issue=issue_description,
            repo=repo
        )

        return result

    except Exception as e:

        if self.request.retries < self.max_retries:
            wait_time = 2 ** self.request.retries
            raise self.retry(countdown=wait_time, exc=e)
        
        return {
            "group_id": file_group.get('group_id', 'unknown'),
            "status": "failed",
            "files": [],
            "error": str(e)
        }