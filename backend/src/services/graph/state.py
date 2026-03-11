"""
AutoDev State Management

This module defines the state schema for the AutoDev  orchestrator.
Uses a hybrid approach:
- TypedDict for main state (LangGraph compatibility with add_messages)
- Dataclasses for sub-objects (clean typing + methods)
- Helper functions for state transformations (immutable updates)
"""

import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

# ============================================
# INTERNAL HELPER FUNCTIONS: Immutable state operations
# ============================================

def update_counter(current: int, update: int | None) -> int:
    """
    If update is 0, reset.
    If update is positive, increment.
    """
    if update == 0:
        return 0  
    if update is None:
        return current  
    
    return current + update

def add_floats(current: float, increment: float | None) -> float:
    """
    Reducer for accumulating floating point values (e.g., costs).
    
    Args:
        current: Current accumulated value
        increment: Value to add (or None for no change)
    
    Returns:
        Updated accumulated value
    
    Examples:
        add_floats(1.50, 0.25) -> 1.75
        add_floats(1.50, None) -> 1.50  # No change
        add_floats(0.0, 0.05) -> 0.05
    """

    if increment is None:
        return current
    return round(current + increment, 6)

# ============================================
# SUB-OBJECTS: Dataclasses for structured data
# ============================================

@dataclass
class AutoDevError:
    """
    Structured error tracking for observability.
    
    Attributes:
        step: Which orchestration step failed (e.g., "planning", "coding")
        error_type: Category of error for filtering/alerting
        message: Human-readable error description
        timestamp: When the error occurred
        traceback: Full Python traceback for debugging (optional)
    """

    step: str
    error_type: Literal["tool_error", "llm_error", "validation_error", "timeout"]
    message: str
    timestamp: datetime
    traceback: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization"""
        return {
            "step": self.step,
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback
        }
    
@dataclass
class TestResult:
    """
    Individual test execution result from sandbox.
    
    Attributes:
        test_name: Name/identifier of the test (e.g., "test_user_login")
        passed: Whether the test succeeded
        output: Test output/logs
        duration_seconds: How long the test took to run
        error: Error message if test failed (optional)
    """

    test_name: str
    passed: bool
    output: str
    duration_seconds: float
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization"""
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "output": self.output,
            "duration_seconds": self.duration_seconds,
            "error": self.error
        }
    
# ============================================
# MAIN STATE: TypedDict for LangGraph compatibility
# ============================================

class AutoDevState(TypedDict):
    """
    Main orchestration state for AutoDev ReAct agent.
    
    ARCHITECTURE DECISION:
    - Uses TypedDict (not @dataclass) to ensure LangGraph's `add_messages`
      reducer works correctly with the Annotated messages field
    - Sub-objects (AutoDevError, TestResult) use dataclasses for clean typing
    - Helper functions provide state transformation logic
    
    STATE LIFECYCLE:
    1. Created via create_initial_state() factory
    2. Nodes return partial dict updates (immutable pattern)
    3. LangGraph merges updates into state
    4. Checkpointed for resume/recovery
    """

    # ============================================
    # REQUIRED INPUTS (set at initialization)
    # ============================================
    issue_id: str 
    """GitHub issue ID being processed"""

    issue_description: str
    """Full text of the GitHub issue"""
    
    repo_name: str
    """Repository name (e.g., 'owner/repo')"""
    
    branch_name: str
    """Target branch for PR (e.g., 'main', 'develop')"""
    
    user_id: str
    """User who initiated this run (for multi-tenancy)"""
    
    session_id: str
    """Unique run identifier (UUID) for tracking"""
    
    # ============================================
    # ENGINE: ReAct message history
    # ============================================
    messages: Annotated[list[AnyMessage], add_messages]
    """
    LangGraph ReAct loop history:
    - HumanMessage: Initial query
    - AIMessage: LLM reasoning and tool calls
    - ToolMessage: Tool execution results
    
    The add_messages reducer ensures new messages are appended correctly.
    """

    # ============================================
    # NODE STATE: Context Retrieval Phase
    # ============================================
    retrieved_files: Optional[list[dict[str, Any]]]
    """
    Files retrieved from context assembly.
    Format: [
        {
            "file_path": str,
            "summary": str,
            "signatures": str, 
            "imports": list[str]
        }
    ]
    """

    repo_context: Optional[dict[str, Any]]
    """
    Repository metadata from context assembly.
    Format: {
        "repo_name": str,
        "language_stack": list[str]
    }
    """

    manifests: Optional[dict[str, str]]
    """
    Project manifest files (package.json, requirements.txt, etc.).
    Format: {"frontend/package.json": "<content>", ...}
    """

    # ============================================
    # NODE STATE: Planning Phase
    # ============================================
    execution_plan: Optional[dict[str, Any]]
    """
    Complete execution plan from Planner agent.
    Format: {
        "understanding": str,  # High-level analysis of the issue
        "file_groups": [  # Grouped file changes with dependencies
            {
                "group_id": str,
                "description": str,
                "files": [
                    {
                        "file_path": str,
                        "action": "create" | "modify" | "delete",
                        "changes": str,
                        "reason": str
                    }
                ],
                "dependencies": list[str],  # Other group_ids this depends on
                "can_parallelize": bool
            }
        ],
        "execution_order": list[str],  # group_ids in execution order
        "sandbox_config": {
            "runtimes": list[str],  # e.g., ["python", "node"]
            "setup_commands": list[str],
            "test_commands": list[str]
        }
    }
    """
    
    files_to_modify: list[str]
    """
    Flattened list of file paths from execution_plan.
    Extracted for quick UI tree view rendering.
    """

    # ============================================
    # NODE STATE: Coding Phase
    # ============================================
    generated_code: dict[str, str]
    """
    Generated code by file path.
    Format: {"/path/to/file.py": "new content"}
    """

    code_generation_errors: list[dict[str, Any]]
    """Errors encountered during code generation"""

    # ============================================
    # NODE STATE: Testing Phase
    # ============================================
    sandbox_logs: list[str]
    """Raw logs from sandbox execution"""

    test_results: Optional[list[TestResult]]
    """Parsed test results (list of TestResult dataclass instances)"""

    test_status: Literal["pending", "running", "passed", "failed"]
    """Overall test execution status"""

    # ============================================
    # NODE STATE: Review Phase
    # ============================================
    review_feedback: Optional[str]
    """Feedback from code review agent"""
    
    review_status: Literal["pending", "approved", "changes_requested"]
    """Review decision status"""

    # ============================================
    # NODE STATE: PR Creation Phase
    # ============================================
    pr_url: Optional[str]
    """URL of created pull request"""
    
    pr_number: Optional[int]
    """GitHub PR number"""

    # ============================================
    # ORCHESTRATION CONTROL
    # ============================================
    current_step: Literal[
        "retrieving_context",
        "planning",
        "coding",
        "testing",
        "reviewing",
        "creating_pr",
        "completed",
        "failed"
    ]
    """Current phase in the orchestration pipeline"""

    approval_gates: dict[str, Literal["pending", "approved", "rejected"]]
    """
    Human-in-the-loop approval tracking.
    Format: {"context": "approved", "plan": "pending", "code": "pending"}
    """

    tool_call_counts: dict[str, int]
    """Track how many times each tool has been called"""

    retry_count: Annotated[int, update_counter]
    """Number of retry attempts for current step"""
    
    max_retries: int
    """Maximum allowed retries before aborting"""
    
    errors: list[AutoDevError]
    """List of errors encountered (AutoDevError dataclass instances)"""
    

    # ============================================
    # OBSERVABILITY
    # ============================================
    llm_model: str
    """LLM model being used (e.g., 'gpt-4', 'claude-sonnet-4')"""
    
    estimated_cost_usd: Annotated[float, add_floats]
    """Running total of estimated API costs. Uses add_floats reducer to increment cost for each LLM call."""
    
    started_at: datetime
    """When this run was initiated"""
    
    updated_at: datetime
    """Last state update timestamp"""
    
    completed_at: Optional[datetime]
    """When the run completed (success or failure)"""

# ============================================
# EXTERNAL HELPER FUNCTIONS: Immutable state operations
# ============================================
def is_approved(state: AutoDevState, gate: str) -> bool:
    """
    Check if a specific approval gate is approved.
    
    Args:
        state: Current AutoDev state
        gate: Gate to check (e.g., "context", "plan", "code")
    
    Returns:
        True if gate is approved, False otherwise
    """
    return state["approval_gates"].get(gate) == "approved"

def add_error(
    state: AutoDevState,
    step: str,
    error: Exception,
    error_type: Literal["tool_error", "llm_error", "validation_error", "timeout"] = "tool_error"
) -> dict[str, Any]:
    """
    Add an error to state and increment retry count.
    
    This is a helper for nodes to construct partial state updates.
    Returns a dict to be merged into state (immutable pattern).
    
    Args:
        state: Current AutoDev state
        step: Which step failed
        error: The exception that occurred
        error_type: Category of error
    
    Returns:
        Partial state update dict with new error and incremented retry count
    
    Example:
        >>> return add_error(state, "planning", ValueError("Invalid plan"))
    """

    error_obj = AutoDevError(
        step=step,
        error_type=error_type,
        message=str(error),
        timestamp=datetime.now(),
        traceback=traceback.format_exc()
    )

    return {
        "errors": state["errors"] + [error_obj],
        "retry_count": state["retry_count"] + 1,
        "updated_at": datetime.now()
    }


def should_abort(state: AutoDevState) -> bool:
    """
    Check if we've exceeded max retries and should abort.
    
    Args:
        state: Current AutoDev state
    
    Returns:
        True if retry count >= max retries
    """
    return state["retry_count"] >= state["max_retries"]

def extract_files_from_context(context_data: dict[str, Any]) -> list[str]:
    """
    Extract file paths from context assembler output.
    
    Args:
        context_data: The full context dict from ContextAssembler
            Format: {
                "issue": {...},
                "repo_context": {...},
                "files": [{"file_path": str, ...}],
                "manifests": {...}
            }
    
    Returns:
        List of file paths that were retrieved
    
    Example:
        >>> context = {
        ...     "files": [
        ...         {"file_path": "frontend/src/components/Node.tsx", ...},
        ...         {"file_path": "backend/src/models/graph.py", ...}
        ...     ]
        ... }
        >>> extract_context_files(context)
        ['frontend/src/components/Node.tsx', 'backend/src/models/graph.py']
    """

    files = context_data.get("files", [])
    return [file["file_path"] for file in files]

def extract_files_from_plan(execution_plan: dict[str, Any]) -> list[str]:
    """
    Extract all file paths from an execution plan.
    
    Flattens the file_groups structure to get a simple list of paths
    for UI rendering (e.g., tree view of files to be modified).
    
    Args:
        execution_plan: The execution plan from Planner agent
    
    Returns:
        List of file paths to be modified/created/deleted
    
    Example:
        >>> plan = {
        ...     "file_groups": [
        ...         {"files": [{"file_path": "src/foo.py"}, {"file_path": "src/bar.py"}]},
        ...         {"files": [{"file_path": "tests/test_foo.py"}]}
        ...     ]
        ... }
        >>> extract_files_from_plan(plan)
        ['src/foo.py', 'src/bar.py', 'tests/test_foo.py']
    """

    files = []
    for group in execution_plan.get("file_groups", []):
        for file_spec in group.get("files", []):
            files.append(file_spec["file_path"])
    return files

def mark_step_complete(
    state: AutoDevState,
    next_step: Literal[
        "retrieving_context",
        "planning",
        "coding",
        "testing",
        "reviewing",
        "creating_pr",
        "completed",
        "failed"
    ]
) -> dict[str, Any]:
    """
    Mark current step as complete and transition to next step.
    
    Args:
        state: Current AutoDev state
        next_step: The step to transition to
    
    Returns:
        Partial state update dict
    """

    update = {
        "current_step": next_step,
        "updated_at": datetime.now()
    }
    
    if next_step in ("completed", "failed"):
        update["completed_at"] = datetime.now()
    
    return update

# ============================================
# INITIATE STATE
# ============================================
def create_initial_state(
    issue_id: str,
    issue_description: str,
    repo_name: str,
    branch_name: str,
    user_id: str,
    session_id: str,
    llm_model: str = "claude-sonnet-4-20250514",
    max_retries: int = 3
) -> AutoDevState:
    """
    Factory function for creating initial AutoDev state with sensible defaults.
    
    This is the ONLY way to create a new AutoDevState - it ensures all required
    fields are populated and defaults are set correctly.
    
    Args:
        issue_id: GitHub issue ID
        issue_description: Full issue text
        repo_name: Repository name (e.g., 'owner/repo')
        branch_name: Target branch for PR
        user_id: User initiating the run
        session_id: Unique run identifier (UUID)
        llm_model: LLM to use (default: gpt-4)
        max_retries: Maximum retry attempts (default: 3)
    
    Returns:
        Fully initialized AutoDevState ready for orchestration
    
    Example:
        >>> state = create_initial_state(
        ...     issue_id="123",
        ...     issue_description="Add user authentication",
        ...     repo_name="acme/webapp",
        ...     branch_name="main",
        ...     user_id="user_abc",
        ...     session_id=str(uuid.uuid4())
        ... )
    """

    now = datetime.now()

    return AutoDevState(

        # Required inputs
        issue_id=issue_id,
        issue_description=issue_description,
        repo_name=repo_name,
        branch_name=branch_name,
        user_id=user_id,
        session_id=session_id,

        # Engine
        messages=[],
        
        # Domain state - Context
        retrieved_files=None,
        repo_context=None,
        manifests=None,
        context_summary=None,
        
        # Domain state - Planning
        execution_plan=None,
        files_to_modify=[],
        
        # Domain state - Coding
        generated_code={},
        code_generation_errors=[],
        
        # Domain state - Testing
        sandbox_logs=[],
        test_results=None,
        test_status="pending",
        
        # Domain state - Review
        review_feedback=None,
        review_status="pending",

        # Domain state - PR
        pr_url=None,
        pr_number=None,
        
        # Orchestration control
        current_step="retrieving_context",
        approval_gates={
            "context": "pending",
            "plan": "pending",
            "code": "pending"
        },
        tool_call_counts={},
        retry_count=0,
        max_retries=max_retries,
        errors=[],
        
        # Observability
        llm_model=llm_model,
        estimated_cost_usd=0.0,
        started_at=now,
        updated_at=now,
        completed_at=None
    )