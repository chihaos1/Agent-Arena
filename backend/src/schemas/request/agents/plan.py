from typing import Annotated
from pydantic import BaseModel, Field

from schemas.response.agents.context import ContextAssemblerResponse

class PlanRequest(BaseModel):
    context: ContextAssemblerResponse
    
    model_preference: Annotated[
        str,
        Field(
            default="claude-sonnet-4-20250514", 
            description="Which LLM to use for planning",
            example=["gpt-4o"]
        )
    ]
    
    max_iterations: Annotated[
        int,
        Field(
            default=3, 
            description="Retry limit for valid plan generation",
            examples=[3]
        )
    ]