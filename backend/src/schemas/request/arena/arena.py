from typing import Annotated
from pydantic import BaseModel, Field, SecretStr

class StrategyConfig(BaseModel):
    """Configuration for a single Arena strategy."""
    
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
    
    model: Annotated[
        str,
        Field(
            description="LLM model to use for this strategy",
            examples=["gpt-4o", "claude-sonnet-4-20250514", "gpt-4o-mini"]
        )
    ]
    
    temperature: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Sampling temperature (0.0 = deterministic, 1.0 = creative)",
            examples=[0.0, 0.3, 0.7, 1.0]
        )
    ]

class ArenaRequest(BaseModel):
    """
    Request to run TraceGraph Arena: 3 strategies compete on the same task.
    
    Arena runs 3 different model/temperature combinations in parallel,
    allowing direct comparison of cost, speed, and quality.
    """

    issue_id: Annotated[
        str,
        Field(
            description="GitHub issue number or identifier",
            examples=["42", "1"]
        )
    ]

    issue_description: Annotated[
        str,
        Field(
            description="Full GitHub issue description that defines the task",
            examples=[
                "Add color prop to Node component",
                "Implement dark mode toggle in settings",
                "Fix memory leak in WebSocket connection"
            ]
        )
    ]

    repo_name: Annotated[
        str,
        Field(
            description="Repository in format: owner/repo",
            examples=["facebook/react"]
        )
    ]

    strategies: Annotated[
        list[StrategyConfig],
        Field(
            min_length=3,
            max_length=3,
            description="Exactly 3 strategies to compare (A, B, C)",
            examples=[[
                {
                    "version_id": "strategy_a",
                    "strategy_name": "GPT-4o Creative",
                    "model": "gpt-4o",
                    "temperature": 0.7
                },
                {
                    "version_id": "strategy_b",
                    "strategy_name": "Claude Deterministic",
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.0
                },
                {
                    "version_id": "strategy_c",
                    "strategy_name": "Mini Budget",
                    "model": "gpt-4o-mini",
                    "temperature": 0.0
                }
            ]]
        )
    ]