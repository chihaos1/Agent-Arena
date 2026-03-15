import copy
import json
import logging
from typing import Tuple, List, Dict

from litellm import completion
from github.Repository import Repository

from core.config import settings

logger = logging.getLogger(__name__)

class CoderAgent:
    """Generates code for a single file group"""

    def __init__(self, model: str = None, temperature: float = 0.0):
        self.model = model or "claude-sonnet-4-20250514"
        self.temperature = temperature

    def generate_code(self, file_group: dict, understanding: str, issue: str, repo: Repository) -> dict:
        """
        Generate code for ONE file group.
        
        Args:
            file_group: File group from execution plan
            understanding: Overall understanding from plan
            issue: Original issue description
            repo: GitHub repo object
        
        Returns:
            {
                "files": [{"path": "...", "content": "..."}],
                "reasoning": str
            }
        """

        logger.info(f"Generating code for group: {file_group['group_id']}")

        # Fetch files from Github
        file_group = self._fetch_files(file_group, repo)

        # Build prompts
        prompt = self._build_code_generation_prompt(file_group, understanding, issue)

        # Generate code and reasoning
        files, reasoning = self._generate_code(prompt)

        return {
            "files": files,
            "reasoning": reasoning
        }

    def _fetch_files(self, file_group: dict, repo: Repository) -> dict:
        """Fetch existing file contents"""
        
        file_group = copy.deepcopy(file_group)
        
        for file in file_group["files"]:
            if file["action"] == "modify":
                try:
                    content = repo.get_contents(file["file_path"]).decoded_content.decode("utf-8", errors="ignore")
                    file["content"] = content
                    logger.info(f"Fetched {file['file_path']}")
                except Exception as e:
                    logger.warning(f"Could not fetch {file['file_path']}: {e}")
                    file["content"] = None
            else:
                file["content"] = None
        
        return file_group

    def _generate_code(self, prompt: str) -> Tuple[List[Dict], str]:
        """Generate the code based on instruction from the Planner"""

        logger.info(f"Calling LLM for code generation: model={self.model}, temp={self.temperature}")

        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            tools=[self._get_tool_schema()],
            tool_choice={"type": "function", "function": {"name": "generate_code"}},
            temperature=self.temperature,
            max_tokens=8000
        )

        # Extract tool call from response
        assistant_message = response.choices[0].message
        
        if not hasattr(assistant_message, "tool_calls") or not assistant_message.tool_calls:
            logger.error("No tool calls found in response")
            return [], ""
        
        tool_call = assistant_message.tool_calls[0]
        
        # Parse tool_call
        args = json.loads(tool_call.function.arguments)
        files = args.get("files", [])
        reasoning = args.get("reasoning", "")

        logger.info(f"Generated {len(files)} files")
        
        return files, reasoning

    def _get_tool_schema(self) -> dict:
        """Tool schema for generating code"""

        return {
            "type": "function",
            "function": {
                "name": "generate_code",
                "description": "Generated code files with complete contents based on user intent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "Your analysis of how these files work together, what dependencies exist, and what imports are needed. This helps ensure consistency."
                        },
                        "files": {
                            "type": "array",
                            "description": "Array of generated files with complete contents",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "The exact file path"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "The complete file content"
                                    }
                                },
                                "required": ["path", "content"]
                            }
                        }
                    },
                    "required": ["reasoning", "files"]
                }
            }
        }

    def _build_code_generation_prompt(self, file_group: dict, understanding: str, issue: str) -> str:
        """Build initial generation prompt"""
        
        files_section = ""
        for file in file_group["files"]:
            files_section += f"\n{'='*60}\n"
            files_section += f"File: {file['file_path']}\n"
            files_section += f"Action: {file['action']}\n"
            files_section += f"Changes: {file['changes']}\n"
            
            if file.get("content"):
                files_section += f"\nCurrent:\n```\n{file['content']}\n```\n"
            else:
                files_section += "\n(New file)\n"
        
        return f"""
        
            You are implementing a focused code change for a GitHub issue.

            ## Task
            Issue: {issue}
            Goal: {file_group.get('description')}
            Strategy: {understanding}

            ## Files
            {files_section}

            ## Output requirements
            - Complete files only — no snippets, no TODOs, no placeholders
            - Match existing code style exactly (indentation, naming, patterns)
            - Preserve all existing exports, props, and functions
            - Only change what the task requires — nothing more
            - Add imports for new dependencies, remove unused ones
            - If files reference each other, keep types and interfaces consistent

            ## Runtime constraints
            - Node.js 18 | Python 3.12 | Go 1.21
            - No Node 20+ APIs | No vite@7+ | No Python 3.13+ features
            - New npm packages must declare Node 18 support in their engines field

            Use generate_code to return all {len(file_group['files'])} files.
            
        """