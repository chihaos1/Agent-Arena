from typing import Annotated

from pydantic import BaseModel, Field

class SearchContextResponse(BaseModel):
    """Response after embedding user's repo into Pinecone"""


    query: Annotated[
        str,
        Field(
            description="GitHub issue that was used to searched against the vector store",
            examples=["Add Dark Mode to website"]
        )
    ]

    relevant_files: Annotated[
        list,
        Field(
            description="A list of scripts that is relevant to the query",
            examples=["backend/src/app.py", "backend/src/api/routes.py"]
        )
    ]