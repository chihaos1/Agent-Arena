"""
Context Retrieval Tool

LangGraph-compatible tool that wraps ContextAssembler.
Enables the ReAct agent to search the codebase and retrieve relevant files.
"""

import logging
import traceback
from datetime import datetime
from typing import Annotated
from langchain_core.tools import tool
from pydantic import Field

from services.domain.context.assembler import ContextAgent
from services.graph.state import AutoDevError

logger = logging.getLogger(__name__)

def create_context_tool(github_token: str, strategy_name: str):
    """
    Creates a context retrieval tool using ContextAssembler.
    
    Args:
        github_token: GitHub Personal Access Token (bound at creation time)
    
    Returns:
        LangGraph tool function that can be called by the ReAct agent
    
    Example:
        >>> tool = create_context_tool(github_token="ghp_...")
        >>> # LLM can now call: retrieve_context(query="...", repo_name="...")
    """

    assembler = ContextAgent(github_token=github_token, strategy_name=strategy_name)

    @tool
    def retrieve_context(
        query: Annotated[str, Field(description="The issue description or search query to find relevant files")],
        repo_name: Annotated[str, Field(description="Repository name in format 'owner/repo' (e.g., 'facebook/react')")]
    ) -> dict:
        """
        Search the codebase and retrieve relevant files for a given issue or query.
        
        Uses semantic search (Pinecone) to find relevant files, fetches them from GitHub,
        and parses code signatures using Tree-sitter.
        
        Returns a context package containing:
        - retrieved_files: List of relevant files with summaries and code signatures
        - repo_context: Repository metadata (name, language stack)
        
        Do NOT rename or restructure fields.
        """

        logger.info(f"retrieve_context called: query='{query[:50]}...', repo={repo_name}")

        try:

            context = assembler.assemble_context(
                query=query,
                repo_name=repo_name
            )

            files_count = len(context.get("files", []))
            logger.info(f"Context retrieved successfully: {files_count} files")
            
            return {
                "retrieved_files": context["files"],
                "repo_context": context["repo_context"],
                "current_step": "planning",
                "completed_step": "retrieving_context",
                "updated_at": datetime.now()
            }
        
        except Exception as e:

            logger.error(
                f"Context retrieval failed for repo={repo_name}: {type(e).__name__}: {str(e)}", 
                exc_info=True
            )
            
            return {
                "errors": [AutoDevError(
                    step="retrieving_context",
                    error_type="tool_error",
                    message=str(e),
                    timestamp=datetime.now(),
                    traceback=traceback.format_exc()
                )],
                "retry_count": 1,
                "completed_step": "retrieving_context",
                "current_step": "failed",
                "completed_step": "retrieving_context",
                "updated_at": datetime.now()
            }
        
    return retrieve_context