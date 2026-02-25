from typing import TypedDict, List, Dict

from schemas.response.agents.plan import FileGroup

class CoderState(TypedDict):
    """State for the coder workflow."""

    # Input
    file_group: dict
    understanding: str
    issue: str
    repo: any

    # Generated code
    generated_files: List[Dict]
    reasoning: str
    
    # # Validation
    # is_valid: bool
    # errors: List[str]
    # retry_count: int
    
    # # Output
    # result: Dict


