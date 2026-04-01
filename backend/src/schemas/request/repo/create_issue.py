from typing import Annotated
from pydantic import BaseModel, Field

class CreateIssueRequest(BaseModel):
    """Request to create a GitHub issue on the sandbox repo"""

    repo_name: Annotated[
        str,
        Field(
            description="Repository in format: owner/repo",
            examples=["chihaos1/jira_clone"]
        )
    ]

    title: Annotated[
        str,
        Field(
            description="GitHub issue title",
            examples=["Add placeholder text to issue title input"]
        )
    ]

    body: Annotated[
        str,
        Field(
            description="GitHub issue body describing the task",
            examples=["Add a placeholder text that says 'Enter issue title...' to the title input field"]
        )
    ]