from typing import Annotated

from pydantic import BaseModel, Field

class EmbedRepoResponse(BaseModel):
    """Response after embedding user's repo into Pinecone"""

    success: Annotated[
        bool,
        Field(
            description="Boolean flag to indicate if repo was successfully embedded",
            examples=[True, False]
        )
    ]

    files_embedded: Annotated[
        int,
        Field(
            description="The total number of files embedded to Pinecone",
            examples=[36]
        )
    ]

    namespace: Annotated[
        str,
        Field(
            description="The Pinecone namespace that stores the user's GitHub repo",
            examples=["facebook_react", "chihaos1_ThinkNode"]
        )
    ]

    message: Annotated[
        str,
        Field(
            description="The message to confirm repo embedding success",
            examples=["Successfuly embedded to facebook_react"]
        )
    ]