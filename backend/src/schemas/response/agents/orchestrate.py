from typing import Annotated, List

from pydantic import BaseModel, Field

class OrchestrateResponse(BaseModel):
    query: Annotated[
            str, 
            Field(
                description="The original user request or GitHub issue used for retrieval",
                example=["Add Dark Mode to website"]
            )
        ]