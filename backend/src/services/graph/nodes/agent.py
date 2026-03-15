"""
ReAct Agent

Core reasoning loop that observes state and decides next actions.
Uses LiteLLM for model-agnostic LLM calls.
"""

import json
import logging
import traceback
from datetime import datetime
from typing import List

from litellm import completion, completion_cost
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from ..state import AutoDevState, AutoDevError
from services.observability.posthog_client import posthog

logger = logging.getLogger(__name__)

def serialize_messages(messages: List) -> str:
    """Serialize last 5 messages as JSON for PostHog."""

    try:
        recent_messages = messages[-5:] if len(messages) > 5 else messages
        serialized = []

        for message in recent_messages:
            if hasattr(message, "content"):
                serialized.append({
                    "role": type(message).__name__.replace("Message", "").lower(),
                    "content": str(message.content)[:500]
                })
        return json.dumps(serialized)
    except:
        return "[serialization_failed]"

def _convert_to_dict(message) -> dict:
    """
    Convert LangChain message objects to dict format for LiteLLM.
    
    Args:
        msg: LangChain message (AIMessage, ToolMessage, etc.)
    
    Returns:
        Dict in OpenAI format that LiteLLM can translate to any provider
    """

    if isinstance(message, AIMessage): 
        message_dict = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tool_call["id"],
                    "type": "function",
                    "function": {
                        "name": tool_call["name"],
                        "arguments": json.dumps(tool_call["args"])
                    }
                }
                for tool_call in message.tool_calls
            ]
        return message_dict
    elif isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content
        }
    else:
        return {
            "role": getattr(message, "role", "user"),
            "content": str(message.content)
        }

def prepare_messages(state: AutoDevState, system_prompt: SystemMessage) -> list[dict]:
    """
    Convert all messages to LiteLLM-compatible dict format.
    
    Args:
        state: Current AutoDev state
        system_prompt: System prompt (LangChain SystemMessage)
    
    Returns:
        List of message dicts in OpenAI format
    """
    messages = [
        {"role": "system", "content": system_prompt.content}
    ]

    # For Anthropic model specifically, as it requires a non-system message in the initial call
    if not state["messages"]:
        messages.append({
            "role": "user",
            "content": f"Begin working on: {state['issue_description']}"
        })
    
    for message in state["messages"]:
        messages.append(_convert_to_dict(message))
    
    return messages

def build_system_prompt(state: AutoDevState) -> SystemMessage:
    """
    Construct system prompt that gives agent context about current state.
    
    The prompt tells the agent:
    - What task it's working on
    - What's been completed so far
    - What tools are available
    - That it has full autonomy to decide the order
    """

    # Dynamic guide for tool responsibilities
    step_to_tool = {
        "retrieving_context": ("retrieve_context", "fetch relevant files from the repo (call once)"),
        "planning":           ("create_plan",       "structure the implementation from retrieved context"),
        "coding":             ("generate_code",     "write the actual code changes"),
        "creating_pr":        ("create_pr",         "open the pull request — only when everything looks good"),
    }

    current_tool, _ = step_to_tool.get(
        state["current_step"], ("unknown", "unknown step — stop and report")
    )

    tool_responsibilities = "\n".join([
        f"  - {tool}: {desc} {'← YOU ARE HERE' if tool == current_tool else ''}"
        for _ , (tool, desc) in step_to_tool.items()
    ])

    # Build context for current progress
    prompt = f"""

        You are AutoDev, an autonomous coding agent that transforms GitHub issues into production-ready pull requests.

        ## Task
        Issue #{state['issue_id']}: {state['issue_description']}
        Repository: {state['repo_name']} | Branch: {state['branch_name']}
        Current step: {state['current_step']}

        ## Tool responsibilities
        {tool_responsibilities}

        ## Tool data integrity
        Pass tool outputs to the next tool exactly as received. Do not rename or restructure fields.

        ## Rules
        1. Pass tool outputs to the next tool exactly as received
        2. Use actual tool results from state, not assumptions
        3. Retry failed tools once with corrected inputs, then stop

        ## Examples
        After create_plan completes, state contains execution_plan.
        When calling generate_code:
            CORRECT: generate_code(execution_plan=<from state>, issue_description="...", repo_name="...")
            WRONG: generate_code(issue_description="...", repo_name="...")  // Missing execution_plan!
                
        """
    
    return SystemMessage(content=prompt)

def track_llm_generation(
    state: AutoDevState,
    messages: list,
    response,
    duration: float,
    cost: float
):
    """Track LLM generation event to PostHog."""
    session_id = state.get('session_id', 'unknown')
    assistant_message = response.choices[0].message
    
    posthog.capture(
        distinct_id=session_id,
        event='$ai_generation',
        properties={
            '$ai_model': state['llm_model'],
            '$ai_input': serialize_messages(messages),
            '$ai_output': assistant_message.content or "[tool_calls]",
            '$ai_input_tokens': response.usage.prompt_tokens,
            '$ai_output_tokens': response.usage.completion_tokens,
            '$ai_latency_ms': duration,
            '$ai_cost_usd': cost,
            '$ai_trace_id': session_id,
            'arena_trace_id': state.get('arena_trace_id'),
            'version_id': state.get('version_id'),
            'strategy_name': state.get('strategy_name'),
            'model': state['llm_model'],
            'temperature': state.get('temperature'),
            'version_id': state.get('version_id'),
            'phase': state['current_step'],
            'timestamp': datetime.now().isoformat()
        }
    )

def track_agent_error(state: AutoDevState, error: Exception):
    """Track agent error event to PostHog."""
    session_id = state.get('session_id', 'unknown')
    
    posthog.capture(
        distinct_id=session_id,
        event='agent_error',
        properties={
            'phase': state['current_step'],
            'error_type': type(error).__name__,
            'error_message': str(error),
            '$ai_trace_id': session_id,
            'arena_trace_id': state.get('arena_trace_id'),
            'version_id': state.get('version_id'),
            'strategy_name': state.get('strategy_name'),
            'model': state['llm_model'],
            'temperature': state.get('temperature'),
            'timestamp': datetime.now().isoformat()
        }
    )

def agent(state: AutoDevState, tools: list[BaseTool]) -> dict:
    """
    Core ReAct reasoning loop using LiteLLM.
    
    The agent observes current state and decides:
    - Which tool to call next
    - Whether to request approval
    - Whether work is complete
    
    Args:
        state: Current AutoDev state
        tools: List of available LangGraph tools
    
    Returns:
        Partial state update with LLM's decision (new messages)
    """

    session_id = state.get('session_id', 'unknown')
    strategy_context = f"[{state.get('version_id', 'unknown')}|{state.get('strategy_name', 'unknown')}]"
    
    logger.info(
        f"{strategy_context} Agent reasoning: "
        f"session={session_id}, "
        f"step={state['current_step']}, "
        f"retry={state['retry_count']}, "
        f"model={state['llm_model']}, "
        f"temp={state.get('temperature', 0.0)}"
    )

    # 1. Build system prompt with most recent context
    system_prompt = build_system_prompt(state)

    # 2. Aggregate messages for LLM (system prompt + conversation history)
    messages = prepare_messages(state, system_prompt)
    
    # 3. Convert LangChain tools to LiteLLM format
    tool_schemas = [convert_to_openai_tool(tool) for tool in tools]

    try:
        # 4. Call LLM via LiteLLM 
        logger.debug(
            f"{strategy_context} Calling LLM: "
            f"model={state['llm_model']}, "
            f"temp={state['temperature']}"
        )

        start_time = datetime.now()
        response = completion(
            model=state["llm_model"],
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
            temperature=state["temperature"]
        )
        duration = (datetime.now() - start_time).total_seconds()

        # 5. Extract the response message
        assistant_message = response.choices[0].message

        # 6. Calculate cost of the query
        cost = completion_cost(completion_response=response)
        logger.info(f"{strategy_context} LLM call cost: ${cost:.6f}")
        track_llm_generation(state, messages, response, duration, cost)

        # 7. Log what tool the agent called
        langchain_tool_calls = []

        if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
            tool_names = [tool_call.function.name for tool_call in assistant_message.tool_calls]
            logger.info(f"{strategy_context} Agent decided to call tools: {tool_names}")

            if assistant_message.content:
                logger.info(f"{strategy_context} Agent reasoning: {assistant_message.content}")

            # 8. Convert LiteLLM tool calls to LangGraph format (converting so Langgraph can call the tool)
            for tool_call in assistant_message.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments)
                    langchain_tool_calls.append({
                        "name": tool_call.function.name,
                        "args": args,
                        "id": tool_call.id
                    })
                except json.JSONDecodeError as e:
                    logger.error(f"{strategy_context} Failed to parse tool arguments: {tool_call.function.arguments}, error: {e}")
                    continue
        else:
            content_preview = assistant_message.content[:100] if assistant_message.content else "No content"
            logger.info(f"{strategy_context} Agent reasoning: {content_preview}...")

        # 9. Create LangGraph-compatible AIMessage
        ai_message = AIMessage(
            content="", #assistant_message.content
            tool_calls=langchain_tool_calls
        )

        logger.info(f"Total messages in context: {len(state['messages'])}")
        logger.info(f"Message types: {[type(m).__name__ for m in state['messages'][-10:]]}")

        # 10. Update state with new message and cost
        return {
            "messages": [ai_message],
            "estimated_cost_usd": cost,
            "updated_at": datetime.now()
        }

    except Exception as e:
        logger.error(f"{strategy_context} Agent node failed: {e}", exc_info=True)
        track_agent_error(state, e)

        return {
            "errors": [AutoDevError(
                step="agent_reasoning",
                error_type="llm_error",
                message=str(e),
                timestamp=datetime.now(),
                traceback=traceback.format_exc()
            )],
            "retry_count": 1, 
            "current_step": "failed",
            "updated_at": datetime.now()
        }