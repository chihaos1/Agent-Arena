"""
Code Generation Tool

LangGraph-compatible tool that wraps CoderAgent.
Enables the ReAct agent to generate code for file groups from the execution plan.
"""

import logging
import traceback
from typing import Annotated, Optional
from datetime import datetime

from github import Github, Auth
from langchain_core.tools import tool
from pydantic import Field

from services.domain.code.coder import CoderAgent
from services.graph.state import AutoDevError

logger = logging.getLogger(__name__)

def create_coder_tool(github_token: str):
    """
    Creates a code generation tool using CoderAgent.
    
    Processes all file groups in the execution plan sequentially,
    generating complete file contents for each group.
    
    Args:
        github_token: GitHub Personal Access Token (bound at creation time)
    
    Returns:
        LangGraph tool function that can be called by the ReAct agent
    
    Example:
        >>> tool = create_coder_tool(github_token="ghp_...")
        >>> # LLM can now call: generate_code(
        ...     execution_plan={...},
        ...     issue_description="...",
        ...     repo_name="owner/repo"
        ... )
    """
    
    coder = CoderAgent()

    @tool
    def generate_code(
        execution_plan: Annotated[dict, Field(description="Execution plan from create_plan with file_groups and execution_order")],
        issue_description: Annotated[str, Field(description="Original GitHub issue description")],
        repo_name: Annotated[str, Field(description="Repository name in format 'owner/repo' (e.g., 'facebook/react')")],
        generated_files: Annotated[Optional[list[dict]], Field(description="Previously generated files (for retry after test failure)")] = None,
        test_results: Annotated[Optional[list[dict]], Field(description="Test results from run_sandbox (only provide when retrying after test failure)")] = None
    ) -> dict:
        """
        Generate code for all file groups in the execution plan.
        
        Processes file groups sequentially according to execution_order:
        1. Fetches existing file contents from GitHub (for modifications)
        2. Generates complete file contents using CoderAgent
        3. Aggregates results across all groups
        
        If test_results is provided (from a previous run_sandbox failure):
        - Extracts error messages from failed tests
        - Uses correction prompt with error feedback
        - Attempts to fix the specific issues identified
        
        Returns state update with:
        - generated_files: All generated files with complete contents
        - group_results: Summary of each group's generation
        - current_step: Set to "testing" for next phase

        Do NOT rename or restructure fields
        """

        logger.info(f"Generating code for {len(execution_plan['file_groups'])} groups")

        try:
            github_auth = Auth.Token(github_token)

            with Github(auth=github_auth) as client:
                repo = client.get_repo(repo_name)

                # 1. Normalize keys before passing to CoderAgent
                for group in execution_plan["file_groups"]:
                    
                    # Group-level field
                    if "name" in group and "group_id" not in group:
                        group["group_id"] = group["name"]
                    
                    # File-level fields
                    normalized_files = []
                    for file in group.get("files", []):
                        normalized_files.append({
                            "file_path": file.get("file_path") or file.get("path") or file.get("filepath", ""),
                            "action": file.get("action") or file.get("change_type") or file.get("modification_type", "modify"),
                            "changes": file.get("changes") or file.get("description") or file.get("modifications", ""),
                        })
                    
                    group["files"] = normalized_files

                # 2. Extract errors from test results if this is a retry
                test_errors = None
                if test_results:
                    logger.info("Retry attempt with test results")
                    
                    # Aggregate all errors from failed tests
                    error_messages = []
                    for test in test_results:
                        if not test.get("passed") and test.get("error"):
                            error_messages.append(
                                f"Test '{test.get('test_name')}' failed:\n{test.get('error')}\n"
                            )
                    
                    test_errors = "\n".join(error_messages) if error_messages else "Tests failed with no specific error messages"

                # 3. Iterate based on execution order
                all_files = []
                group_results = []

                for group_id in execution_plan["execution_order"]:
                    group = next(
                        (group for group in execution_plan["file_groups"] if group["group_id"] == group_id), 
                        None
                    )

                    if not group:
                        logger.error(f"Group {group_id} not found")
                        continue

                    logger.info(f"Processing group: {group_id}")

                    # Build previous_attempt if retrying
                    previous_attempt = None
                    if test_errors:
                        previous_attempt = {
                            "files": generated_files,  
                            "reasoning": execution_plan.get("understanding", ""),
                            "test_feedback": test_errors 
                        }

                    # Send group to generate code
                    result = coder.generate_code(
                        file_group=group,
                        understanding=execution_plan["understanding"],
                        issue=issue_description,
                        repo=repo,
                        previous_attempt=previous_attempt
                    )
                    
                    # Add result to group results and generated files to all files
                    group_results.append({
                        "group_id": group_id,
                        "files_count": len(result["files"]),
                        "reasoning": result["reasoning"]
                    })

                    all_files.extend(result["files"])
                    logger.info(f"Generated files for Group {group_id}: {len(result['files'])} files")
            
            logger.info(f"Code generation complete: {len(all_files)} files")

            return {
                "generated_files": all_files,
                "group_results": group_results,
                "current_step": "testing",
                "updated_at": datetime.now()
            }

        except Exception as e:
            logger.error(f"Code generation failed: {e}", exc_info=True)
            
            return {
                "errors": [AutoDevError(
                    step="coding",
                    error_type="generation_error",
                    message=str(e),
                    timestamp=datetime.now(),
                    traceback=traceback.format_exc()
                )],
                "current_step": "failed",
                "updated_at": datetime.now()
            }
    
    return generate_code