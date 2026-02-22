from typing import Annotated
from pydantic import BaseModel, Field, SecretStr

class OrchestrateRequest(BaseModel):
    """Request to query GitHub issue in Pinecone to retrieve relevant script locations"""

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

    query: Annotated[
        str,
        Field(
            description="GitHub issue that will be used to searched against the vector store",
            examples=["Add Dark Mode to website"]
        )
    ]