"""
Conditional Routing Functions

Determines graph flow based on state:
- When to execute tools
- When to request approval
- When to loop back to agent
- When to end the workflow
"""

import logging

from typing import Literal
from ..state import AutoDevState

logger = logging.getLogger(__name__)

EXECUTE_TOOLS = "execute_tools"
APPROVAL = "approval"
AGENT = "agent"
END = "end"
GATE_MAP = {
        # "retrieving_context": "context",
        # "planning": "plan",
        # "coding": "code"
    }

def should_continue(state: AutoDevState) -> Literal["execute_tools", "approval", "end"]:
    """Route after agent decides"""

    # Safety: max iterations
    if state["retry_count"] >= state["max_retries"]:
        logger.warning(f"Max retries exceeded for session {state['session_id']}")
        return END
    
    # Completed or failed
    if state["current_step"] in ("completed", "failed"):
        logger.info(f"Workflow ended: {state['current_step']}")
        return END

    # Check if tool call requires approval
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        gate = GATE_MAP.get(state["current_step"])
        
        # TEMPORARY GATE
        if state["current_step"] == "testing":
            logger.info("Planning complete - ending workflow (no testing tool yet)")
            return "end"

        if gate and state["approval_gates"].get(gate) == "pending":
            logger.info(f"Approval required for '{gate}' gate")
            return APPROVAL

        logger.info("Proceeding to tool execution")
        return EXECUTE_TOOLS
    
    # No tool call, end the agent
    logger.info("No tools called, ending workflow")
    return END

def after_execution(state: AutoDevState) -> Literal["agent", "end"]:
    """
    Route after tool execution.
    
    Always loops back to agent unless max iterations or terminal state.
    """
    
    # Safety check
    if state["retry_count"] >= state["max_retries"]:
        logger.warning("Max retries exceeded after execution")
        return END
    
    # Check terminal states
    if state["current_step"] in ("completed", "failed"):
        logger.info(f"Terminal state reached: {state['current_step']}")
        return END
    
    # Loop back to agent
    logger.info("Looping back to agent")
    return AGENT

def after_approval(state: AutoDevState) -> Literal["execute_tools", "end"]:
    """
    Route after human approval decision.
    
    Approved: execute tools
    Rejected: end workflow
    """
    
    gate = GATE_MAP.get(state["current_step"])
    
    if gate and state["approval_gates"].get(gate) == "approved":
        logger.info(f"Approval gate '{gate}' approved")
        return EXECUTE_TOOLS
    
    logger.info(f"Approval gate '{gate}' rejected or not found")
    return END