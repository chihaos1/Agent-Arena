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

def normalize_execution_plan(execution_plan: dict, strategy_name: str) -> dict:
    """
    Normalize execution plan to handle variations from different LLMs.
    
    Handles:
    - Different field names (group_name vs group_id, path vs file_path)
    - Files as strings vs objects
    - execution_order as indices vs group_ids
    """
    
    # Normalize file groups
    for idx, group in enumerate(execution_plan.get("file_groups", [])):
        
        # Ensure group has group_id
        if "group_id" not in group:
            group["group_id"] = (
                group.get("group_name") or 
                group.get("name") or 
                f"group_{idx}"
            )
            logger.warning(f"{strategy_name}: Added missing group_id - {group['group_id']}")
        
        # Normalize files
        normalized_files = []
        for file in group.get("files", []):
            if isinstance(file, str): #Files as strings vs objects
                normalized_files.append({
                    "file_path": file,
                    "action": "modify",
                    "changes": ""
                })
            else:
                normalized_files.append({ #Fix any wrong field name
                    "file_path": file.get("file_path") or file.get("path") or file.get("filepath", ""),
                    "action": file.get("action") or file.get("change_type") or file.get("modification_type", "modify"),
                    "changes": file.get("changes") or file.get("description") or file.get("modifications", ""),
                })
        
        group["files"] = normalized_files
    
    # Normalize execution_order
    execution_order = execution_plan.get("execution_order", [])
    
    if execution_order and isinstance(execution_order[0], int):
        logger.warning(f"{strategy_name}: execution_order contains indices, mapping to group_ids")
        execution_order = [
            execution_plan["file_groups"][idx].get("group_id", f"group_{idx}")
            for idx in execution_order
            if idx < len(execution_plan["file_groups"])
        ]
        execution_plan["execution_order"] = execution_order
    
    return execution_plan

def create_coder_tool(github_token: str, strategy_name: str, model: str, temperature: float):
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
    
    coder = CoderAgent(model=model, temperature=temperature)

    @tool
    def generate_code(
        execution_plan: Annotated[dict, Field(description="Execution plan from create_plan with file_groups and execution_order")],
        issue_description: Annotated[str, Field(description="Original GitHub issue description")],
        repo_name: Annotated[str, Field(description="Repository name in format 'owner/repo' (e.g., 'facebook/react')")],
    ) -> dict:
        """
        Generate code for all file groups in the execution plan.
        
        Processes file groups sequentially according to execution_order:
        1. Fetches existing file contents from GitHub (for modifications)
        2. Generates complete file contents using CoderAgent
        3. Aggregates results across all groups
        
        Returns state update with:
        - generated_files: All generated files with complete contents
        - group_results: Summary of each group's generation
        - current_step: Set to "creating_pr" for next phase

        Do NOT rename or restructure fields
        """

        logger.info(f"{strategy_name}: Generating code for {len(execution_plan['file_groups'])} groups")

        try:
            github_auth = Auth.Token(github_token)

            with Github(auth=github_auth) as client:
                repo = client.get_repo(repo_name)
                
                # 1. Normalize the execution plan
                execution_plan = normalize_execution_plan(execution_plan, strategy_name)

                # 3. Iterate based on execution order
                all_files = []
                group_results = []

                for group_id in execution_plan["execution_order"]:
                    group = next(
                        (group for group in execution_plan["file_groups"] if group["group_id"] == group_id), 
                        None
                    )

                    if not group:
                        logger.error(f"{strategy_name}: Group {group_id} not found")
                        continue

                    logger.info(f"{strategy_name}: Processing group - {group_id}")

                    # Send group to generate code
                    result = coder.generate_code(
                        file_group=group,
                        understanding=execution_plan.get("understanding", ""),
                        issue=issue_description,
                        repo=repo,
                    )
                    
                    # Add result to group results and generated files to all files
                    group_results.append({
                        "group_id": group_id,
                        "files_count": len(result["files"]),
                        "reasoning": result["reasoning"]
                    })

                    all_files.extend(result["files"])
                    logger.info(f"{strategy_name}: Generated files for Group {group_id}: {len(result['files'])} files")
            
            logger.info(f"{strategy_name}: Code generation complete with {len(all_files)} files")

            return {
                "generated_files": all_files,
                "group_results": group_results,
                "current_step": "creating_pr",
                "completed_step": "coding",
                "updated_at": datetime.now()
            }

        except Exception as e:
            logger.error(f"{strategy_name}:Code generation failed: {e}", exc_info=True)
            
            return {
                "errors": [AutoDevError(
                    step="coding",
                    error_type="generation_error",
                    message=str(e),
                    timestamp=datetime.now(),
                    traceback=traceback.format_exc()
                )],
                "current_step": "failed",
                "completed_step": "coding",
                "updated_at": datetime.now()
            }
    
    return generate_code