"""
Tool Executor

Executes tool calls decided by the agent.
Separates decision-making (agent) from execution (this node).
"""

import json
import logging
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from services.observability.posthog_client import posthog

from ..state import AutoDevState

logger = logging.getLogger(__name__)

PHASE_MAP = {
    'retrieve_context': 'retrieving_context',
    'create_plan': 'planning',
    'generate_code': 'coding',
    'create_pr': 'reviewing'
}

def track_phase_entered(state: AutoDevState, phase: str, tool_name: str):
    """Track when agent enters a new phase."""
    session_id = state.get('session_id', 'unknown')
    
    posthog.capture(
        distinct_id=session_id,
        event='agent_phase_entered',
        properties={
            'phase': phase,
            'tool': tool_name,
            'arena_trace_id': state.get('arena_trace_id'),
            'version_id': state.get('version_id'),
            'strategy_name': state.get('strategy_name'),
            'model': state.get('llm_model'),
            'temperature': state.get('temperature'),
            'timestamp': datetime.now().isoformat()
        }
    )

def track_tool_called(state: AutoDevState, phase: str, tool_name: str, duration: float):
    """Track successful tool execution."""
    session_id = state.get('session_id', 'unknown')
    
    posthog.capture(
        distinct_id=session_id,
        event='agent_tool_called',
        properties={
            'phase': phase,
            'tool': tool_name,
            'total_duration_s': duration,
            'success': True,
            'arena_trace_id': state.get('arena_trace_id'),
            'version_id': state.get('version_id'),
            'strategy_name': state.get('strategy_name'),
            'model': state.get('llm_model'),
            'temperature': state.get('temperature'),
            'timestamp': datetime.now().isoformat()
        }
    )

def track_phase_exited(state: AutoDevState, phase: str, duration: float, success: bool = True):
    """Track when agent exits a phase."""
    session_id = state.get('session_id', 'unknown')
    
    posthog.capture(
        distinct_id=session_id,
        event='agent_phase_exited',
        properties={
            'phase': phase,
            'total_duration_s': duration,
            'success': success,
            'arena_trace_id': state.get('arena_trace_id'),
            'version_id': state.get('version_id'),
            'strategy_name': state.get('strategy_name'),
            'model': state.get('llm_model'),
            'temperature': state.get('temperature'),
            'timestamp': datetime.now().isoformat()
        }
    )

def track_tool_failed(state: AutoDevState, phase: str, tool_name: str, error: Exception):
    """Track tool execution failure."""
    session_id = state.get('session_id', 'unknown')
    
    posthog.capture(
        distinct_id=session_id,
        event='agent_tool_failed',
        properties={
            'phase': phase,
            'tool': tool_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'arena_trace_id': state.get('arena_trace_id'),
            'version_id': state.get('version_id'),
            'strategy_name': state.get('strategy_name'),
            'model': state.get('llm_model'),
            'temperature': state.get('temperature'),
            'timestamp': datetime.now().isoformat()
        }
    )

def create_tool_summary(state: AutoDevState, tool_name: str, result: dict) -> str:
    """Create agent-readable summary of tool execution results."""

    if tool_name == "retrieve_context":
        files = result.get("retrieved_files", [])
        file_list = "\n".join([f"- {file['file_path']}" for file in files])
        
        return f"""
        
        retrieve_context completed.

        Retrieved {len(files)} files:
        {file_list}

        Ready for create an execution plan with create_plan."""
    
    elif tool_name == "create_plan":
        plan = result.get("execution_plan", {})
        groups = plan.get("file_groups", [])
        files_to_modify = result.get("files_to_modify", [])

        return f"""
        
        create_plan completed.

        Created execution plan:
        - {len(groups)} file groups
        - {len(files_to_modify)} total files to modify

        Ready to start coding with generate_code"""
    
    elif tool_name == "generate_code":
        files = result.get("generated_files", [])
        file_list = "\n".join([f"- {file['path']}" for file in files])
        
        return f"""
        
        generate_code completed.

        Generated {len(files)} files:
        {file_list}

        Ready to create pull request with create_pr
        
        """

    elif tool_name == "create_pr":
        pr_url = result.get("pr_url", "")
        pr_number = result.get("pr_number", 0)

        return f"""
        
        create_pr completed

        PR #{pr_number}: {pr_url}

        Workflow complete"""

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

    # 1. Get the session ID from the state
    session_id = state.get('session_id')
    strategy_context = f"[{state.get('version_id', 'unknown')}|{state.get('strategy_name', 'unknown')}]"

    if not session_id or session_id == 'unknown':
        logger.warning(f"{strategy_context}: No session_id in state")

    logger.info(f"{strategy_context}: Tool executor starting for session {session_id}")

    # 1. Get the last message from agent
    if not state["messages"]:
        logger.warning(f"{strategy_context}: No messages in state, nothing to execute")
        return {}

    # 2. Check if there are tool calls to execute
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.info(f"{strategy_context}: No tool calls in last message, skipping execution")
        return {}

    # 3. Execute each tool call sequentially
    tool_messages = []
    state_updates = {}

    for tool_call in last_message.tool_calls:
        
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

        logger.info(f"{strategy_context}: Executing tool - {tool_name} with args - {tool_args}")

        # Tracking for PostHog
        phase = PHASE_MAP.get(tool_name)
        if phase:
            track_phase_entered(state, phase, tool_name)

        try:
            if tool_name not in tools:
                raise ValueError(f"Tool '{tool_name}' not found in available tools: {list(tools.keys())}")
            
            tool_function = tools[tool_name]

            # Execute the tool
            start_time = datetime.now()
            result = tool_function.invoke(tool_args)
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"{strategy_context}: Tool {tool_name} completed successfully in {duration:.2f}s")

            # Unpack tool result to update the state
            if isinstance(result, dict):
                state_updates.update(result)

                # Create ToolMessage with summary (summary differs for each tool)
                summary = create_tool_summary(state, tool_name, result) or f"{tool_name} completed."

                tool_message = ToolMessage(
                    content=summary,
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                    
                logger.debug(f"{strategy_context}: Tool {tool_name} updated fields: {list(result.keys())}")

            else:
                logger.warning(f"{strategy_context}: Tool {tool_name} returned non-dict result: {type(result)}")
                
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                    name=tool_name
                )

            # Tracking for PostHog
            track_tool_called(state, phase, tool_name, duration)
            if phase:
                track_phase_exited(state, phase, duration, success=True)
            
            tool_messages.append(tool_message)

        except Exception as e:
            logger.error(f"{strategy_context}: Tool {tool_name} failed: {e}", exc_info=True)           
            error_message = f"Tool '{tool_name}' failed with error: {type(e).__name__}: {str(e)}"
            
            tool_message = ToolMessage(
                content=error_message,
                tool_call_id=tool_call_id,
                name=tool_name
            )

            # Tracking for PostHog
            track_tool_failed(state, phase, tool_name, e)
            
            tool_messages.append(tool_message)

    logger.info(
        f"{strategy_context}: Tool execution completed. "
        f"Returning {len(tool_messages)} messages and {len(state_updates)} state updates"
    )
    
    return {
        "messages": tool_messages,
        **state_updates  # Unpack all state updates from tools (e.g., retrieved_files, current_step)
    }