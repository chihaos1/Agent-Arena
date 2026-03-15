from typing import Annotated
from pydantic import BaseModel, Field

class StrategyResult(BaseModel):
    """
    Result from a single strategy execution in Arena.
    
    Contains performance metrics and outcome for one model/temperature combination.
    """

    version_id: Annotated[
        str,
        Field(
            description="Strategy identifier: strategy_a, strategy_b, or strategy_c",
            examples=["strategy_a", "strategy_b", "strategy_c"]
        )
    ]

    strategy_name: Annotated[
        str,
        Field(
            description="Human-readable strategy name",
            examples=["GPT-4o Creative", "Claude Deterministic", "Mini Budget"]
        )
    ]

    success: Annotated[
        bool,
        Field(
            description="Whether the strategy completed successfully",
            examples=[True, False]
        )
    ]

    cost_usd: Annotated[
        float,
        Field(
            description="Total LLM cost in USD for this strategy",
            examples=[0.42, 0.38, 0.15]
        )
    ]

    duration_seconds: Annotated[
        int,
        Field(
            description="Total execution time in seconds",
            examples=[45, 28, 52]
        )
    ]

    pr_url: Annotated[
        str | None,
        Field(
            default=None,
            description="GitHub pull request URL if PR was created",
            examples=["https://github.com/facebook/react/pull/10"]
        )
    ]

    pr_number: Annotated[
        int | None,
        Field(
            default=None,
            description="GitHub pull request number if PR was created",
            examples=[10, 11, 12]
        )
    ]

    step_reached: Annotated[
        str | None,
        Field(
            default=None,
            description="Final workflow step reached",
            examples=["completed", "failed", "coding"]
        )
    ]

    error: Annotated[
        str | None,
        Field(
            default=None,
            description="Error message if strategy failed",
            examples=[
                "LLM API rate limit exceeded",
                "GitHub authentication failed"
            ]
        )
    ]

class ArenaResponse(BaseModel):
    """
    Response from Arena run containing results from all 3 strategies.
    
    Provides comparison data for cost, speed, and quality across strategies.
    """

    arena_trace_id: Annotated[
        str,
        Field(
            description="Unique identifier grouping all 3 strategy runs together",
            examples=["arena-abc-123", "arena-f3e2d1c0-4b5a-6789-0123-456789abcdef"]
        )
    ]

    duration_seconds: Annotated[
        int,
        Field(
            description="Total Arena execution time (all 3 strategies run in parallel)",
            examples=[62, 45, 70]
        )
    ]

    strategies: Annotated[
        list[StrategyResult],
        Field(
            description="Results from all 3 strategies for side-by-side comparison",
            min_length=3,
            max_length=3
        )
    ]