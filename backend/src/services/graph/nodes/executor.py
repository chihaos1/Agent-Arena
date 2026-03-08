"""
Tool Executor

Executes tool calls decided by the agent.
Separates decision-making (agent) from execution (this node).
"""

import logging
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from ..state import AutoDevState

logger = logging.getLogger(__name__)

def create_tool_summary(tool_name: str, result: dict) -> str:
    """Create agent-readable summary of tool execution results."""

    if tool_name == "retrieve_context":
        files = result.get("retrieved_files", [])
        file_list = "\n".join([f"- {file['file_path']}" for file in files])
        
        return f"Retrieved {len(files)} files:\n{file_list}\n\nReady to create plan."


def tool_executor(state: AutoDevState, tools: dict[str, BaseTool]) -> dict:
    """
    Execute tool calls from the agent's last message.
    
    Unpacks tool results into state updates. Since AutoDev tools return
    state update dictionaries (e.g., {"retrieved_files": [...], "current_step": "planning"}),
    this node merges those updates into the top-level state.

    Args:
        state: Current AutoDev state
        tools: Dictionary mapping tool names to tool functions
               Example: {"retrieve_context": <tool_function>, ...}
    
    Returns:
        State update with:
        - messages: ToolMessages with execution summaries
        - [tool-specific fields]: Unpacked from tool results (e.g., retrieved_files, execution_plan)
    """

    logger.info(f"Tool executor starting for session {state['session_id']}")

    # 1. Get the last message from agent
    if not state["messages"]:
        logger.warning("No messages in state, nothing to execute")
        return {}

    # 2. Check if there are tool calls to execute
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.info("No tool calls in last message, skipping execution")
        return {}
    
    logger.info(f"Executing {len(last_message.tool_calls)} tool call(s)")

    # 3. Execute each tool call sequentially
    tool_messages = []
    state_updates = {}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

        try:
            if tool_name not in tools:
                raise ValueError(f"Tool '{tool_name}' not found in available tools: {list(tools.keys())}")
            
            tool_function = tools[tool_name]

            # Execute the tool
            start_time = datetime.now()
            result = tool_function.invoke(tool_args)
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"Tool {tool_name} completed successfully in {duration:.2f}s")

            # Unpack tool result to update the state
            if isinstance(result, dict):
                state_updates.update(result)

                # Create ToolMessage with summary (summary differs for each tool)
                summary = create_tool_summary(tool_name, result)

                tool_message = ToolMessage(
                    content=summary,
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                    
                logger.debug(f"Tool {tool_name} updated fields: {list(result.keys())}")

            else:
                logger.warning(f"Tool {tool_name} returned non-dict result: {type(result)}")
                
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
            
            tool_messages.append(tool_message)

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)            
            error_message = f"Tool '{tool_name}' failed with error: {type(e).__name__}: {str(e)}"
            
            tool_message = ToolMessage(
                content=error_message,
                tool_call_id=tool_call_id,
                name=tool_name
            )
            
            tool_messages.append(tool_message)

    logger.info(
        f"Tool execution completed. "
        f"Returning {len(tool_messages)} messages and {len(state_updates)} state updates"
    )
    
    return {
        "messages": tool_messages,
        **state_updates  # Unpack all state updates from tools (e.g., retrieved_files, current_step)
    }