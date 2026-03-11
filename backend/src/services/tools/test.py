"""
Sandbox Testing Tool

LangGraph-compatible tool that wraps TestAgent.
Enables the ReAct agent to execute tests in isolated environment.
"""

import logging
import traceback
from typing import Annotated
from datetime import datetime
from langchain_core.tools import tool
from pydantic import Field

from services.domain.test.tester import TestAgent
from services.graph.state import AutoDevError

logger = logging.getLogger(__name__)

def create_sandbox_tool(github_token: str):
    """
    Creates a sandbox testing tool using TestAgent.
    
    Args:
        github_token: GitHub Personal Access Token (bound at creation time)
    
    Returns:
        LangGraph tool function that can be called by the ReAct agent
    
    Example:
        >>> tool = create_sandbox_tool(github_token="ghp_...")
        >>> # LLM can now call: run_sandbox(
        ...     generated_files=[...],
        ...     sandbox_config={...},
        ...     repo_name="owner/repo"
        ... )
    """
    
    tester = TestAgent(github_token=github_token)

    @tool
    def run_sandbox(
        generated_files: Annotated[list[dict], Field(description="Generated files from generate_code with 'path' and 'content' fields")],
        sandbox_config: Annotated[dict, Field(description="Sandbox configuration from execution_plan with runtimes, setup_commands, test_commands")],
        repo_name: Annotated[str, Field(description="Repository name in format 'owner/repo' (e.g., 'facebook/react')")]
    ) -> dict:
        """
        Execute generated code in isolated sandbox environment.
        
        Runs setup commands (e.g. npm install, pip install) and test commands
        (e.g. npm test, pytest) in a Docker container.
        
        Returns state update with:
        - test_result: Detailed output from sandbox
        - test_status: "passed" or "failed"
        - current_step: Next workflow step
        
        Do NOT rename or restructure fields.
        """

        logger.info(
            f"run_sandbox called: {len(generated_files)} files, "
            f"config={sandbox_config}"
        )

        try:
            # Execute tests via TestAgent
            result = tester.run_tests(
                generated_files=generated_files,
                sandbox_config=sandbox_config,
                repo_name=repo_name
            )

            success = result.get("passed", False)
            logger.info(f"Sandbox execution completed: success={success}")

            output = result.get("output", "")
            logger.info(f"Sandbox execution output: {output}")

            # Determine next step based on results
            next_step = "reviewing" if success else "failed"
            test_status = "passed" if success else "failed"

            return {
                "test_results": result,
                "test_status": test_status,
                "current_step": next_step,
                "updated_at": datetime.now()
            }

        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}", exc_info=True)
            
            return {
                "errors": [AutoDevError(
                    step="testing",
                    error_type="sandbox_error",
                    message=str(e),
                    timestamp=datetime.now(),
                    traceback=traceback.format_exc()
                )],
                "test_status": "failed",
                "current_step": "failed",
                "updated_at": datetime.now()
            }
    
    return run_sandbox