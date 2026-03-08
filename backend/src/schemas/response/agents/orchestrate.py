from pydantic import BaseModel, Field
from typing import Annotated, Optional


class OrchestrateResponse(BaseModel):
    workflow_id: Annotated[
        str,
        Field(
            description="Unique identifier for this workflow session",
            example="550e8400-e29b-41d4-a716-446655440000"
        )
    ]
    
    status: Annotated[
        str,
        Field(
            description="Current workflow status",
            example="completed"
        )
    ]
    
    pr_url: Annotated[
        Optional[str],
        Field(
            description="URL of the created pull request if workflow completed successfully",
            example="https://github.com/user/repo/pull/123"
        )
    ] = None
    
    files_modified: Annotated[
        int,
        Field(
            description="Number of files modified in the execution plan",
            example=5
        )
    ] = 0
    
    cost_usd: Annotated[
        float,
        Field(
            description="Estimated total cost of LLM API calls in USD",
            example=0.47
        )
    ] = 0.0