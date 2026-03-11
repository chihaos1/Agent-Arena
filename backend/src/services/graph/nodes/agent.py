"""
ReAct Agent

Core reasoning loop that observes state and decides next actions.
Uses LiteLLM for model-agnostic LLM calls.
"""

import json
import logging
from datetime import datetime
from litellm import completion, completion_cost
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from ..state import AutoDevState, AutoDevError

logger = logging.getLogger(__name__)

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
        "testing":            ("run_sandbox",       "validate the code with tests"),
        "reviewing":          ("review_code",       "quality gate before submitting"),
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

        ## If something goes wrong
        If a tool fails, assess whether a single retry with different inputs makes sense.
        If you still can't proceed after one retry, stop and report what went wrong.
        Retrying the same tool repeatedly will not produce different results.
        
        """
    
    return SystemMessage(content=prompt)
    
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

    logger.info(
        f"Agent reasoning for session {state['session_id']}, "
        f"step: {state['current_step']}, "
        f"retry_count: {state['retry_count']}"
    )

    # 1. Build system prompt with most recent context
    system_prompt = build_system_prompt(state)

    # 2. Aggregate messages for LLM (system prompt + conversation history)
    messages = [system_prompt] + list(state["messages"])
    
    # 3. Convert LangChain tools to LiteLLM format
    tool_schemas = [convert_to_openai_tool(tool) for tool in tools]

    try:
        # 4. Call LLM via LiteLLM 
        logger.debug(f"Calling LLM with model: {state['llm_model']}")

        response = completion(
            model=state["llm_model"],
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
            temperature=0
        )

        # 5. Extract the response message
        assistant_message = response.choices[0].message

        # 6. Calculate cost of the query
        cost = completion_cost(completion_response=response)
        logger.info(f"LLM call cost: ${cost:.6f}")

        # 7. Log what tool the agent called
        langchain_tool_calls = []

        if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
            tool_names = [tool_call.function.name for tool_call in assistant_message.tool_calls]
            logger.info(f"Agent decided to call tools: {tool_names}")

            if assistant_message.content:
                logger.info(f"Agent reasoning: {assistant_message.content}")

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
                    logger.error(f"Failed to parse tool arguments: {tool_call.function.arguments}, error: {e}")
                    continue
        else:
            content_preview = assistant_message.content[:100] if assistant_message.content else "No content"
            logger.info(f"Agent reasoning: {content_preview}...")

        # 9. Create LangGraph-compatible AIMessage
        ai_message = AIMessage(
            content="", #assistant_message.content or 
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
        logger.error(f"Agent node failed: {e}", exc_info=True)
        
        # Return error state update
        import traceback
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