from typing import Annotated

from pydantic import BaseModel, Field

class CreateIssueResponse(BaseModel):
    """Response after successfully creating a GitHub issue"""

    success: Annotated[
        bool,
        Field(
            description="Boolean flag to indicate if issue was successfully created",
            examples=[True, False]
        )
    ]

    issue_number: Annotated[
        int,
        Field(
            gt=0,
            description="The GitHub issue number",
            examples=[42, 123, 1]
        )
    ]

    issue_url: Annotated[
        str,
        Field(
            description="The direct URL to view the issue on GitHub",
            examples=["https://github.com/facebook/react/issues/12345"]
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

    created_at: Annotated[
        str,
        Field(
            description="The timestamp of when the issue was created (UTC)",
            examples=["2024-02-14T10:30:45Z"]
        )
    ]

    message: Annotated[
        str,
        Field(
            description="The message to confirm issue creation success",
            examples=["Issue #1 'Add dark mode support' created in facebook/react"]
        )
    ]