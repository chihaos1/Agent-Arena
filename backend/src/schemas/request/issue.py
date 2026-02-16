from typing import Annotated

from pydantic import BaseModel, Field, SecretStr

class CreateIssueRequest(BaseModel):
    """Request to create issue in user's Github repo"""

    github_token: Annotated[
        SecretStr,
        Field(
            description="GitHub Personal Access Token (masked in logs)",
            examples=["github_pat_00SAMPLE08ww7ySr3Kb6S_AAAV68ftALK3c6Q0JI4dPnGmyWBD6JpuEIjr30vpR1MYVMG4B65MVfx6jtH"]
        )
    ]

    repo_name: Annotated[
        str,
        Field(
            description="Repository in format: owner/repo",
            examples=["facebook/react"]
        )
    ]

    issue_title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=256,
            description="The title of the issue",
            examples=["Fix login bug with special characters"]
        )
    ]

    issue_description: Annotated[
        str,
        Field(
            min_length=1,
            description="The detailed description of the issue",
            examples=["Users cannot login when password contains special characters like @ or #"]
        )
    ]