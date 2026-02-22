from typing import Annotated, List

from pydantic import BaseModel, Field

class IssueModel(BaseModel):
    query: Annotated[
        str, 
        Field(
            description="The original user request or GitHub issue used for retrieval",
            example=["Add Dark Mode to website"]
        )
    ]

class RepoContextModel(BaseModel):
    repo_name: Annotated[
        str,
        Field(
            description="Full name of the repository (owner/repo)",
            examples=["facebook/react"]
        )
    ]

    language_stack: Annotated[
        List[str],
        Field(
            description="List of programming languages detected in the repo",
            examples=[["TypeScript", "Python", "CSS"]]
        )
    ]

class FileContextModel(BaseModel):
    file_path: Annotated[
        str,
        Field(
            description="The path to the file within the repository",
            examples=["frontend/src/App.tsx"]
        )
    ]

    summary: Annotated[
        str,
        Field(
            description="A brief AI-generated summary of the file's purpose.",
            examples=["Defines AuthModal component for handling user authentication."]
        )
    ]

    signatures: Annotated[
        str,
        Field(
            description="Top-level code signatures (classes/functions) of the file",
            examples=["export default function AuthModal({close}: ModalProps) {"]
        )
    ]

    imports: Annotated[
        List[str],
        Field(
            description="List of dependencies and modules imported by the file",
            examples=[["react", "supabase", "./NavBar.css"]]
        )
    ]

class ContextAssemblerResponse(BaseModel):
    """The final structured payload passed to the LLM Planner."""

    issue: IssueModel
    repo_context: RepoContextModel
    files: List[FileContextModel]
