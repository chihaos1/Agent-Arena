"""
AutoDev Graph Builder

Constructs the ReAct graph with:
- Agent reasoning loop
- Tool execution
- Approval gates for human-in-the-loop
- Max iteration safety checks
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AutoDevState
from .nodes.agent import agent
from .nodes.executor import tool_executor
from .routing import should_continue, after_execution, after_approval
from ..tools.context import create_context_tool
from ..tools.plan import create_plan_tool
from ..tools.code import create_coder_tool

logger = logging.getLogger(__name__)

def approve(state: AutoDevState) -> dict:
    """Approval gate - returns empty (handled externally)"""
    logger.info(f"Approval gate triggered for step: {state['current_step']}, session: {state['session_id']}")
    return {}

def build_graph(github_token: str, enable_checkpointing: bool = True):
    """Build the AutoDev ReAct graph"""

    logger.info("Building AutoDev graph...")

    # Create tools
    tools = {
        "retrieve_context": create_context_tool(github_token),
        "create_plan": create_plan_tool(),
        "generate_code": create_coder_tool(github_token)
    }

    logger.info(f"Initialized {len(tools)} tools: {list(tools.keys())}")

    # Build graph
    workflow = StateGraph(AutoDevState)

    # Add nodes
    workflow.add_node("agent", lambda state: agent(state, list(tools.values())))
    workflow.add_node("executor", lambda state: tool_executor(state, tools))
    workflow.add_node("approval", approve)

    # Entry point
    workflow.set_entry_point("agent")

    # Edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"execute_tools": "executor", "approval": "approval", "end": END}
    )

    workflow.add_conditional_edges(
        "approval",
        after_approval,
        {"execute_tools": "executor", "end": END}
    )
    
    workflow.add_conditional_edges(
        "executor",
        after_execution,
        {"agent": "agent", "end": END}
    )

    if enable_checkpointing: 
        logger.info("Compiling graph with checkpointing enabled")
        return workflow.compile(checkpointer=MemorySaver())

    logger.info("Compiling graph without checkpointing")
    return workflow.compile()