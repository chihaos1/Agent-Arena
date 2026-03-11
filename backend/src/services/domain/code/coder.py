import copy
import logging
from typing import Tuple, List, Dict

from anthropic import Anthropic
from github.Repository import Repository

from core.config import settings

logger = logging.getLogger(__name__)

class CoderAgent:
    """Generates code for a single file group"""

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())

    def generate_code(self, file_group: dict, understanding: str, issue: str, repo: Repository, previous_attempt: dict = None) -> dict:
        """
        Generate code for ONE file group.
        
        Args:
            file_group: File group from execution plan
            understanding: Overall understanding from plan
            issue: Original issue description
            repo: GitHub repo object
            previous_attempt: Optional dict when code failed testing:
                - files: Previously generated files
                - reasoning: Previous reasoning
                - test_feedback: Test/compilation errors
        
        Returns:
            {
                "files": [{"path": "...", "content": "..."}],
                "reasoning": str
            }
        """

        logger.info(f"Generating code for group: {file_group['group_id']}")

        # Fetch files from Github
        file_group = self._fetch_files(file_group, repo)

        # Build prompts for either initial or correction code generation
        if previous_attempt:
            logger.info("Building correction prompt with test feedback")
            prompt = self._build_code_correction_prompt(file_group, understanding, issue, previous_attempt
            )
        else:
            logger.info("Building initial generation prompt")
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

        logger.info("Calling Claude for code generation")

        response = self.client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=8000,
            temperature=0,
            tools=[self._get_tool_schema()],
            tool_choice={"type": "tool", "name": "generate_code"},
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract tool_use block
        tool_use = next((block for block in response.content if block.type == "tool_use"), None)

        if not tool_use:
            logger.error("No tool use found in response")
            return [], "" 
        
        files = tool_use.input.get("files", [])
        reasoning = tool_use.input.get("reasoning", "")

        logger.info(f"Generated {len(files)} files")
        
        return files, reasoning

    def _get_tool_schema(self) -> dict:
        """Tool schema for generating code"""

        return {
            "name": "generate_code",
            "description": "Generated code files with complete contents based on user intent",
            "input_schema": {
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
            Goal: {file_group['description']}
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

    def _build_code_correction_prompt(self, file_group: dict, understanding: str, previous_attempt: dict) -> str:
        """Build correction prompt with test feedback when previous code failed the testing"""
        
        # Unpack previous attempt
        previous_files = previous_attempt["files"]
        previous_reasoning = previous_attempt["reasoning"]
        test_feedback = previous_attempt["test_feedback"]
        
        # Show the files that were generated
        files_section = ""
        for file in previous_files:
            files_section += f"\n{'='*60}\n"
            files_section += f"File: {file['path']}\n"
            files_section += f"```\n{file['content']}\n```\n"
        
        return f"""Fix the code based on test/compilation errors.

        **Original Goal:**
        {understanding}

        **This Group's Task:**
        {file_group['description']}

        **Your Previous Reasoning:**
        {previous_reasoning}

        **Your Previous Files:**
        {files_section}

        **Test/Compilation Errors:**
        ```
        {test_feedback}
        ```

        **Instructions:**
        1. Read the errors carefully - they show line numbers and specific issues
        2. Fix ONLY the errors shown (don't rewrite unrelated code)
        3. Common fixes:
            - Import errors → Add missing imports
            - Type errors → Fix type annotations or prop definitions
            - Syntax errors → Check brackets, quotes, semicolons
        4. Return COMPLETE files (not just the fixed parts)
        5. Maintain all existing functionality

        Use generate_code tool to return corrected files.
        """
