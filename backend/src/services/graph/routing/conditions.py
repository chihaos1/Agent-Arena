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
AGENT = "agent"
END = "end"

def should_continue(state: AutoDevState) -> Literal["execute_tools", "end"]:
    """Route after agent decides"""

    # Set max retries
    if state["retry_count"] >= state["max_retries"]:
        logger.warning(f"Max retries exceeded for session {state['session_id']}")
        return END
    
    # Completed or failed
    if state["current_step"] in ("completed", "failed"):
        logger.info(f"Workflow ended: {state['current_step']}")
        return END

    # Route to tool execution if tool call present
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
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
    
    # Set max retries
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