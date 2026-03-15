"""
Create PR Tool

Creates a GitHub pull request with the generated code changes.
"""

import logging
from datetime import datetime
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from services.domain.repo.pull_request import create_pull_request
from services.graph.state import AutoDevError

logger = logging.getLogger(__name__)

def create_pr_tool(github_token: str, strategy_name: str):
    """
    Factory function to create the PR creation tool with GitHub credentials.
    
    Args:
        github_token: GitHub personal access token
    
    Returns:
        Configured create_pr tool
    """

    @tool
    def create_pr(
        issue_id: Annotated[str, Field(description="GitHub issue number being addressed")],
        repo_name: Annotated[str, Field(description="Repository name in format 'owner/repo' (e.g., 'facebook/react')")],
        generated_files: Annotated[list[dict], Field(description="Generated files from generate_code with 'path' and 'content' fields")],
        issue_description: Annotated[str, Field(description="Original GitHub issue description")],
    ) -> dict:
        """
        Create a GitHub pull request with generated code changes.
        
        Creates a new branch from main, commits all generated files,
        and opens a pull request with test results.
        
        Args:
            issue_id: GitHub issue number (used for branch name)
            repo_name: Repository in owner/repo format
            generated_files: List of files with 'path' and 'content'
            issue_description: Original issue text
        
        Returns:
            {
                "pr_url": str,
                "pr_number": int,
                "current_step": "completed"
            }
        """

        logger.info(f"Creating PR for issue #{issue_id} in {repo_name}")
        logger.info(f"Files to commit: {len(generated_files)}")

        try:
            # Call the PR creation script
            result = create_pull_request(
                github_token=github_token,
                issue_id=str(issue_id),
                repo_name=repo_name,
                files=generated_files,
                issue_description=issue_description,
                strategy_name=strategy_name
            )

            logger.info(f"PR created successfully: {result['pr_url']}")
            result["updated_at"] = datetime.now()
            
            return result

        except Exception as e:
            logger.error(f"Failed to create PR: {e}", exc_info=True)
            
            return {
                "errors": [AutoDevError(
                    step="create_pr",
                    error_type="pr_creation_failed",
                    message=f"Failed to create pull request: {str(e)}",
                    timestamp=datetime.now(),
                    traceback=""
                )],
                "current_step": "failed",
                "updated_at": datetime.now()
            }
    
    return create_pr