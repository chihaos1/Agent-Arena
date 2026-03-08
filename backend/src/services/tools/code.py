"""
Code Generation Tool

LangGraph-compatible tool that wraps CoderAgent.
Enables the ReAct agent to generate code for file groups from the execution plan.
"""

import logging
import traceback
from typing import Annotated
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
        repo_name: Annotated[str, Field(description="Repository name in format 'owner/repo' (e.g., 'facebook/react')")]
    ) -> dict:
        """
        Generate code for all file groups in the execution plan.
        
        Processes file groups sequentially according to execution_order:
        1. Fetches existing file contents from GitHub (for modifications)
        2. Generates complete file contents using CoderAgent
        3. Aggregates results across all groups
        
        Note: Validation happens in the testing phase via sandbox execution.
        This tool always returns generated files, even if they contain bugs.
        
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

                # Normalize keys before passing to CoderAgent
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
                
                # Iterate based on execution order

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

                    # Send group to generate code
                    result = coder.generate_code(
                        file_group=group,
                        understanding=execution_plan["understanding"],
                        issue=issue_description,
                        repo=repo
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

            temp = {
                "generated_files": all_files,
                "group_results": group_results,
                "current_step": "testing",
                "updated_at": datetime.now()
            }
            logger.info(f"TEMP CODER RESULT: {temp} ")

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