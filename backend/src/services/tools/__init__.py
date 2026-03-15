"""
Tool Factory

Centralized tool creation for the ReAct agent.
"""

from .context import create_context_tool
from .plan import create_plan_tool
from .code import create_coder_tool
from .create_pr import create_pr_tool

def create_tools(github_token: str, strategy_name: str, model: str, temperature: float) -> dict:
    """
    Create all tools for the ReAct agent.
    
    Args:
        github_token: GitHub Personal Access Token
    
    Returns:
        Dictionary of tool name -> tool function
    """
    return {
        "retrieve_context": create_context_tool(github_token, strategy_name),
        "create_plan": create_plan_tool(strategy_name, model, temperature),
        "generate_code": create_coder_tool(github_token, strategy_name, model, temperature),
        "create_pr": create_pr_tool(github_token, strategy_name)
    }

__all__ = [
    "create_tools",
    "create_context_tool",
    "create_plan_tool", 
    "create_coder_tool",
    "create_pull_request"
]