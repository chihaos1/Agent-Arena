import asyncio
import logging
import json
import time
import uuid
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.request.arena.arena import ArenaRequest
from schemas.response.arena.arena import StrategyResult
from services.graph.state import create_initial_state
from services.graph.builder import build_graph
from services.observability.tracking import (
    track_strategy_started,
    track_strategy_completed,
    track_strategy_failed,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/arena", tags=["arena"])

def create_arena_states(
    arena_trace_id: str,
    request: ArenaRequest
) -> list:
    """Create 3 initial states for Arena strategies"""
    
    states = []
    for strategy in request.strategies:
        state = create_initial_state(
            issue_id=request.issue_id,
            issue_description=request.issue_description,
            repo_name=request.repo_name,
            branch_name="main",
            session_id=str(uuid.uuid4()),
            arena_trace_id=arena_trace_id,
            version_id=strategy.version_id,
            strategy_name=strategy.strategy_name,
            llm_model=strategy.model,
            temperature=strategy.temperature
        )
        states.append(state)
    
    return states

async def run_strategy(
    arena_trace_id: str,
    state: dict,
    graph,   
    queue: asyncio.Queue
) -> StrategyResult:
    """Execute one of the strategies from the group"""

    session_id = state["session_id"]
    version_id = state["version_id"]

    logger.info(f"Running {version_id}: {session_id}")
    track_strategy_started(arena_trace_id, state)

    try:
        # Execute workflow
        start_time = time.time()
        config = {"configurable": {"thread_id": session_id}}

        # Execute asynchronously
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: _stream_graph(graph, state, config, queue, version_id))

        duration = int(time.time() - start_time)
        logger.info(f"{version_id} completed in {duration}s")

        track_strategy_completed(arena_trace_id, state, result, duration)

        return StrategyResult(
            version_id=version_id,
            strategy_name=state["strategy_name"],
            success=True,
            cost_usd=result.get("estimated_cost_usd", 0.0),
            duration_seconds=duration,
            pr_url=result.get("pr_url"),
            pr_number=result.get("pr_number"),
            step_reached=result.get("current_step")
        )

    except Exception as e:
        logger.error(f"{version_id} failed: {e}")
        track_strategy_failed(arena_trace_id, state, e)
        
        return StrategyResult(
            version_id=version_id,
            strategy_name=state["strategy_name"],
            success=False,
            error=str(e),
            cost_usd=0.0,
            duration_seconds=0
        )

def _stream_graph(graph, state, config, queue, version_id):
    """
    Stream LangGraph execution and emit step updates to the SSE queue.
    
    Iterates over graph.stream() chunks, extracting current_step and artifact
    from each state update and putting them into the shared asyncio queue for
    real-time SSE delivery to the frontend.
    
    Returns the final state chunk for use in StrategyResult construction.
    """
    
    last_completed = None
    last_chunk = {}

    for state in graph.stream(state, config, stream_mode="values"):

        current_step = state.get("current_step")
        completed_step = state.get("completed_step")

        if current_step == "failed" and last_completed != "failed":
            queue.put_nowait({
                "version_id": version_id,
                "completed_step": "failed",
                "current_step": "failed",
                "artifact": _extract_artifact(state, "failed")
            })
            last_completed = "failed"
        elif completed_step and completed_step != last_completed:
            queue.put_nowait({
                "version_id": version_id,
                "completed_step": completed_step,
                "current_step": current_step,
                "artifact": _extract_artifact(state, completed_step)
            })
            last_completed = completed_step

        last_chunk = state
    return last_chunk

def _extract_artifact(state: dict, completed_step: str) -> Dict | List | None:
    """
    Extract the relevant artifact from a graph state chunk based on the completed step.

    Maps each workflow step to its corresponding state field and returns
    the artifact in a format suitable for SSE delivery to the frontend.

    Args:
        state: Full graph state snapshot from graph.stream(stream_mode="values")
        completed_step: The step that just finished (e.g., "retrieving_context")

    Returns:
        - retrieving_context: List of file paths retrieved from the repo
        - planning: Execution plan dict with file groups and modification details
        - coding: List of generated file dicts with path and content
        - None if the step has no artifact or the field is missing from state
    """

    if completed_step == "retrieving_context":
        files = state.get("retrieved_files")
        return [file["file_path"] for file in files]
    
    if completed_step == "planning":
        plan = state.get("execution_plan")
        return plan
    
    if completed_step == "coding":
        generated_files = state.get("generated_files")
        return generated_files

    if completed_step == "failed":
        errors = state.get("errors")
        if errors:
            latest = errors[-1]
            return { # E.g. step='retrieving_context', error_type='tool_error', message='404'
                "step": latest.step,
                "error_type": latest.error_type,
                "message": latest.message,
            }
        return None

async def run_strategies(
    arena_trace_id: str,
    states: list,
    github_token: str,
    queue: asyncio.Queue
) -> list[StrategyResult]:
    """Run all 3 strategies in parallel"""

    # Build graphs
    graphs = [
        build_graph(
            github_token=github_token,
            strategy_name=state["strategy_name"],
            model=state["llm_model"],                           
            temperature=state["temperature"], 
            enable_checkpointing=True
        )
        for state in states
    ]

    # Execute all strategies in parallel
    results = await asyncio.gather(
        *[run_strategy(arena_trace_id, state, graph, queue) 
          for state, graph in zip(states, graphs)]
    )

    return results

async def _event_stream(queue, states):
    """
    Async generator that streams SSE events to the frontend.

    Consumes step update events from the shared queue as strategies progress,
    yielding each as a SSE-formatted data string. Tracks completed strategies
    and emits a final 'done' event once all strategies reach a terminal state
    (completed or failed).
    """
    
    completed = 0
    while completed < len(states):
        event = await queue.get()
        yield f"data: {json.dumps(event)}\n\n"
        if event["current_step"] in ("completed", "failed"):
            completed += 1
    
    yield f"data: {json.dumps({'event': 'done'})}\n\n"

@router.post("/stream")
async def run_arena(request: ArenaRequest):
    """Run Arena: 3 strategies compete on the same task"""

    arena_trace_id = f"arena-{uuid.uuid4()}"
    logger.info(f"Arena started: {arena_trace_id}, repo={request.repo_name}")
    
    try:
        states = create_arena_states(arena_trace_id, request)
        queue = asyncio.Queue()
        
        asyncio.create_task(
            run_strategies(
            arena_trace_id,
            states,
            request.github_token.get_secret_value(),
            queue
        ))

        return StreamingResponse(
            _event_stream(queue, states),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    except Exception as e:
        logger.error(f"Arena failed: {arena_trace_id}, error: {e}")
        raise HTTPException(status_code=500, detail=f"Arena failed: {str(e)}")