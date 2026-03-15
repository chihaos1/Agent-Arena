import asyncio
import logging
import time
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException

from schemas.request.arena.arena import ArenaRequest
from schemas.response.arena.arena import ArenaResponse, StrategyResult
from services.graph.state import create_initial_state
from services.graph.builder import build_graph
from services.observability.posthog_client import posthog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/arena", tags=["arena"])

def track_arena_started(arena_trace_id: str, request: ArenaRequest):
    """Track Arena run started in PostHog"""
    
    posthog.capture(
        distinct_id=arena_trace_id,
        event="arena_run_started",
        properties={
            "repo_name": request.repo_name,
            "issue_id": request.issue_id,
            "timestamp": datetime.now().isoformat()
        }
    )

def track_arena_completed(arena_trace_id: str, duration: int, results: list):
    """Track Arena run completed in PostHog."""
    
    posthog.capture(
        distinct_id=arena_trace_id,
        event="arena_run_completed",
        properties={
            "total_duration_s": duration,
            "strategies_completed": len([r for r in results if r.success]),
            "timestamp": datetime.now().isoformat()
        }
    )

def track_arena_failed(arena_trace_id: str, error: Exception):
    """Track Arena run failed in PostHog"""
    
    posthog.capture(
        distinct_id=arena_trace_id,
        event="arena_run_failed",
        properties={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat()
        }
    )

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
) -> StrategyResult:
    """Execute on of the strategies from the group"""

    session_id = state["session_id"]
    version_id = state["version_id"]

    logger.info(f"Running {version_id}: {session_id}")

    # Track started
    track_strategy_started(arena_trace_id, state)

    try:
        # Execute workflow
        start_time = time.time()
        config = {"configurable": {"thread_id": session_id}}

        # Execute asynchronously
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: graph.invoke(state, config))

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
        
        # Track failed
        track_strategy_failed(arena_trace_id, state, e)
        
        # Return failure result
        return StrategyResult(
            version_id=version_id,
            strategy_name=state["strategy_name"],
            success=False,
            error=str(e),
            cost_usd=0.0,
            duration_seconds=0
        )

async def run_strategies(
    arena_trace_id: str,
    states: list,
    github_token: str
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
        *[run_strategy(arena_trace_id, state, graph) 
          for state, graph in zip(states, graphs)]
    )

    return results

@router.post("/", response_model=ArenaResponse)
async def run_arena(request: ArenaRequest):
    """Run Arena: 3 strategies compete on the same task"""

    arena_trace_id = f"arena-{uuid.uuid4()}"
    logger.info(f"Arena started: {arena_trace_id}, repo={request.repo_name}")
    
    # Track Arena started
    track_arena_started(arena_trace_id, request)

    try:
        # Create 3 states
        states = create_arena_states(arena_trace_id, request)

        # Run all 3 in parallel
        start_time = time.time()
        results = await run_strategies(
            arena_trace_id,
            states,
            request.github_token.get_secret_value()
        )

        duration = int(time.time() - start_time)
        logger.info(f"Arena completed: {arena_trace_id} in {duration}s")

        track_arena_completed(arena_trace_id, duration, results)

        return ArenaResponse(
            arena_trace_id=arena_trace_id,
            duration_seconds=duration,
            strategies=results
        )

    except Exception as e:
        logger.error(f"Arena failed: {arena_trace_id}, error: {e}")
        
        # Track Arena failed
        track_arena_failed(arena_trace_id, e)
        
        raise HTTPException(status_code=500, detail=f"Arena failed: {str(e)}")
