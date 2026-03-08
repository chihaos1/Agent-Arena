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

    # Build context for current progress
    progress_context = []

    if state["retrieved_files"]:
        progress_context.append(
            f"Context retrieved: {len(state['retrieved_files'])} files"
        )

    if state["execution_plan"]:
        progress_context.append(
            f"Plan created: {len(state['execution_plan']['file_groups'])} file groups"
        )
    
    if state["generated_code"]:
        progress_context.append(
            f"Code generated: {len(state['generated_code'])} files"
        )
    
    if state["test_status"] != "pending":
        progress_context.append(
            f"Tests run: {state['test_status']}"
        )

    progress = "\n".join(progress_context) if progress_context else "No steps completed yet"

    prompt = f"""
    
        You are AutoDev, an autonomous coding agent that transforms GitHub issues into production-ready pull requests.

        **Current Task:**
        Issue #{state['issue_id']}: {state['issue_description']}
        Repository: {state['repo_name']}
        Branch: {state['branch_name']}

        **Progress So Far:**
        {progress}

        **Current Step:** {state['current_step']}

        **Available Tools:**
        - **retrieve_context**: Search codebase for relevant files
        - **create_plan**: Generate execution plan with file groups
        - **generate_code**: Implement changes based on plan
        - **run_sandbox**: Execute tests in isolated environment
        - **review_code**: AI review of generated code
        - **create_pr**: Submit pull request to GitHub

        **Workflow (Follow Strictly):**
        1. retrieve_context → Get relevant files (ONE comprehensive query)
        2. create_plan → Generate execution plan from context
        3. generate_code → Implement the planned changes
        4. run_sandbox → Test the generated code
        5. review_code → Quality check (if tests pass)
        6. create_pr → Submit the pull request

        **Rules:**
        - Call retrieve_context ONCE with a comprehensive query
        - After retrieve_context completes, you MUST call create_plan next
        - After create_plan completes, you MUST call generate_code next
        - NEVER call retrieve_context after create_plan (generate_code fetches files from GitHub)
        - NEVER call the same tool twice in a row
        - If a ToolMessage says "Ready to X", your next action MUST be X
        - Follow ToolMessage guidance strictly

        **CRITICAL: Tool Data Integrity**
        Pass tool outputs EXACTLY as received from previous tools.
        DO NOT rename fields (e.g., "group_id" → "name", "file_path" → "path").
        Treat tool outputs as opaque - pass them through unchanged.
        
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
            content=assistant_message.content or "",
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