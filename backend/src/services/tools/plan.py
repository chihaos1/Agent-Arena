"""
Planning Tool

LangGraph-compatible tool that wraps PlannerAgent.
Enables the ReAct agent to create execution plans from retrieved context.
"""

import logging
import traceback
from datetime import datetime
from typing import Annotated
from langchain_core.tools import tool
from pydantic import Field

from services.domain.plan.planner import PlannerAgent
from services.graph.state import AutoDevError

logger = logging.getLogger(__name__)

def create_plan_tool():
    """
    Creates a planning tool using PlannerAgent.
    
    Returns:
        LangGraph tool function that can be called by the ReAct agent
    
    Example:
        >>> tool = create_planner_tool()
        >>> # LLM can now call: create_plan(context={...})
    """

    planner = PlannerAgent()

    @tool
    def create_plan(
        context: Annotated[dict, Field(
            description="""
            Complete context for planning. Must include:
            - issue_description: The original task/issue
            - retrieved_files: List of files from context retrieval
            - repo_context: Repository metadata
            - manifests: Project configuration files
            """
        )]
    ) -> dict:
        """
        Create an execution plan from the assembled context.
        
        Analyzes the retrieved files and creates a structured plan with:
        - Understanding of the issue 
        - File groups to modify
        - Execution order
        - Sandbox configuration for testing
        
        Args:
            context: Dictionary with retrieved_files, repo_context, manifests
        
        Returns:
            State update with execution_plan and files_to_modify

        Do NOT rename or restructure fields.
        """

        issue_description = context.get("issue_description", "")
        retrieved_files = context.get("retrieved_files", [])
        repo_context = context.get("repo_context", {})
        manifests = context.get("manifests", {})

        logger.info(
            f"create_plan called: issue='{issue_description[:50]}...', "
            f"files={len(retrieved_files)}"
        )

        try:
            
            # Normalize files keys
            normalized_files = []
            for file in retrieved_files:
                normalized_files.append({
                    "file_path": file.get("file_path") or file.get("path") or file.get("filepath"),
                    "summary": file.get("summary", ""),
                    "signatures": (file.get("signatures") or file.get("code_signatures") or file.get("sig", [])),
                    "imports": file.get("imports", [])
                })

            # Normalize manifests (sometimes passed in a list)
            normalized_manifests = {}
            if isinstance(manifests, list):
                for manifest in manifests:
                    file_path = manifest.get("file_path", "")
                    content = manifest.get("content", "")
                    if file_path:
                        normalized_manifests[file_path] = content
            elif isinstance(manifests, dict):
                normalized_manifests = manifests

            # Transform to the correct context structure
            context = {
                "issue": {
                    "query": issue_description
                },
                "repo_context": repo_context,
                "files": normalized_files, 
                "manifests": normalized_manifests
            }

            # Call PlannerAgent
            execution_plan = planner.create_plan(context)

            # Extract files to modify from plan
            files_to_modify = []
            for group in execution_plan.get("file_groups", []):
                for file in group.get("files", []):
                    files_to_modify.append(file["file_path"])

            logger.info(
                f"Plan created successfully: "
                f"{len(execution_plan.get('file_groups', []))} groups, "
                f"{len(files_to_modify)} files to modify"
            )

            return {
                "execution_plan": execution_plan,
                "files_to_modify": files_to_modify,
                "current_step": "coding",
                "updated_at": datetime.now()
            }

        except Exception as e:
            logger.error(
                f"Plan creation failed: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            
            return {
                "errors": [AutoDevError(
                    step="planning",
                    error_type="tool_error",
                    message=str(e),
                    timestamp=datetime.now(),
                    traceback=traceback.format_exc()
                )],
                "retry_count": 1,
                "current_step": "failed",
                "updated_at": datetime.now()
            }
    
    return create_plan