import json
from datetime import datetime
from typing import List

from .posthog_client import posthog
from services.graph.state import AutoDevState

# ============================================
# Track Agent Strategies
# ============================================

def track_strategy_started(arena_trace_id: str, state: dict):
    """Track individual strategy started in PostHog."""
    
    posthog.capture(
        distinct_id=state["session_id"],
        event="agent_run_started",
        properties={
            "arena_trace_id": arena_trace_id,
            "version_id": state["version_id"],
            "strategy_name": state["strategy_name"],
            "model": state["llm_model"],
            "temperature": state["temperature"],
            "timestamp": datetime.now().isoformat()
        }
    )

def track_strategy_completed(arena_trace_id: str, state: dict, result: dict, duration: int):
    """Track individual strategy completed in PostHog."""
    
    posthog.capture(
        distinct_id=state["session_id"],
        event="agent_run_completed",
        properties={
            "arena_trace_id": arena_trace_id,
            "version_id": state["version_id"],
            "success": True,
            "total_cost_usd": result.get("estimated_cost_usd", 0),
            "total_duration_s": duration,
            "pr_url": result.get("pr_url"),
            "timestamp": datetime.now().isoformat()
        }
    )

def track_strategy_failed(arena_trace_id: str, state: dict, error: Exception):
    """Track individual strategy failed in PostHog."""
    
    posthog.capture(
        distinct_id=state["session_id"],
        event="agent_run_failed",
        properties={
            "arena_trace_id": arena_trace_id,
            "version_id": state["version_id"],
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        }
    )

# ============================================
# Track Agent LLM Calls
# ============================================

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
            '$ai_input': _serialize_messages(messages),
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

def _serialize_messages(messages: List) -> str:
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

# ============================================
# Track Agent Tool Executions
# ============================================

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
