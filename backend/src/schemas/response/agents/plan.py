from typing import Annotated

from pydantic import BaseModel, Field

class PlanResponse(BaseModel):
    query: Annotated[
            str, 
            Field(
                description="The original user request or GitHub issue used for retrieval",
                example=["Add Dark Mode to website"]
            )
        ]