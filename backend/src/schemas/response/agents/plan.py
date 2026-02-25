from typing import List, Literal, Annotated
from pydantic import BaseModel, Field

class FileChange(BaseModel):
    file_path: Annotated[
        str, 
        Field(
            description="The full path to the file relative to repo root",
            examples=["frontend/src/components/3d/graph/Node.tsx"]
        )
    ]

    action: Annotated[
        Literal["modify", "create", "delete"], 
        Field(description="The specific operation to perform")
    ]

    changes: Annotated[
        str, 
        Field(
            description="Detailed description of the code changes required",
            examples=["Replace hardcoded color '#C5C2A8' with node.color property"]
        )
    ]

    reason: Annotated[
        str, 
        Field(
            description="Why this specific change is necessary",
            examples=["Need to store color information in the node data structure"]
        )
    ]

class FileGroup(BaseModel):
    group_id: Annotated[
        str, 
        Field(
            description="A unique identifier for this group of related files",
            examples=["node-color-support"]
        )
    ]

    description: Annotated[
        str, 
        Field(
            description="Summary of what this group of changes achieves",
            examples=["Add color support to node data model and rendering"]
        )
    ]

    files: Annotated[
        List[FileChange], 
        Field(
            description="List of files in this group",
            examples=["""{'file_path': 'frontend/src/models/Graph.ts', 'action': 'modify', 'changes': 'Add optional color property to GraphNode interface with default color value', 'reason': 'Need to store color information in the node data structure'}, {'file_path': 'frontend/src/components/3d/graph/Node.tsx', 'action': 'modify', 'changes': "Replace hardcoded color '#C5C2A8' with node.color property, add fallback to default color if not specified", 'reason': 'Core rendering component needs to use dynamic colors from node data'}"""]
        )
    ]

    dependencies: Annotated[
        List[str], 
        Field(
            description="IDs of other groups that must be completed first",
            default_factory=list,
            examples=[["node-color-support"]]
        )
    ]

    can_parallelize: Annotated[bool, Field(default=False)]

class ExecutionPlanResponse(BaseModel):
    understanding: Annotated[
        str, 
        Field(
            description="The agent's synthesized plan and strategy",
            examples=["The issue requires adding the ability to change node colors..."]
        )
    ]

    file_groups: Annotated[List[FileGroup], Field(description="The categorized batches of files")]

    execution_order: Annotated[
        List[str], 
        Field(
            description="The sequential list of group_ids representing the roadmap",
            examples=[["node-color-support", "color-picker-ui"]]
        )
    ]