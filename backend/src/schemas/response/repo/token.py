from typing import Annotated

from pydantic import BaseModel, Field

class ValidateTokenResponse(BaseModel):
    """Response from validating user-provided GitHub Token"""

    success: Annotated[
        bool,
        Field(
            description="Boolean flag to indicate if token was successfully validated",
            examples=[True, False]
        )
    ]

    repo_name: Annotated[
        str,
        Field(
            description="Repository in format: owner/repo",
            examples=["facebook/react"]
        )
    ]

    repo_url: Annotated[
        str,
        Field(
            description="The URL of the repository",
            examples=["https://github.com/facebook/react"]
        )
    ]

    total_files: Annotated[
        int,
        Field(
            description="The total number of files in the repository",
            examples=[36]
        )
    ]

    message: Annotated[
        str,
        Field(
            description="The message to confirm token validation success",
            examples=["Successfuly connected to facebook/react"]
        )
    ]