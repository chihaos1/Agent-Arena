"""
Tool Factory

Centralized tool creation for the ReAct agent.
"""

from .context import create_context_tool
from .plan import create_plan_tool
from .code import create_coder_tool
from .test import create_sandbox_tool
from .create_pr import create_pr_tool

def create_tools(github_token: str) -> dict:
    """
    Create all tools for the ReAct agent.
    
    Args:
        github_token: GitHub Personal Access Token
    
    Returns:
        Dictionary of tool name -> tool function
    """
    return {
        "retrieve_context": create_context_tool(github_token),
        "create_plan": create_plan_tool(),
        "generate_code": create_coder_tool(github_token),
        "run_sandbox": create_sandbox_tool(github_token),
        "create_pr": create_pr_tool(github_token)
    }

__all__ = [
    "create_tools",
    "create_context_tool",
    "create_plan_tool", 
    "create_coder_tool",
    "create_sandbox_tool",
    "create_pull_request"
]