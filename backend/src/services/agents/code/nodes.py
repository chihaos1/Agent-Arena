import copy
from typing import Dict, List, Tuple

from anthropic import Anthropic

from core.config import settings
from .tools.validate import CodeValidator

def fetch_files(state: Dict) -> Dict:
    """NODE 1: Fetch files from GitHub"""

    file_group = copy.deepcopy(state["file_group"])
    repo = state["repo"]

    for file in file_group["files"]:
        try:
            # Fetch existing files
            if file["action"] == "modify":
                content_raw = repo.get_contents(file["file_path"])
                file["content"] = content_raw.decoded_content.decode("utf-8", errors="ignore")
            else:
                file["content"] = None

        except Exception as e:
            file["content"] = None

    return {"file_group": file_group}

def generate_code(state: Dict) -> Dict:
    """NODE 2: Generate code with Claude using tool use."""

    prompt = _build_generate_code_prompt(state)
    generated_files, reasoning = _generate_code(prompt)
    
    return {
        "generated_files": generated_files,
        "reasoning": reasoning
    }

def validate_code(state: Dict) -> Dict:
    """NODE 3: Validate generated code with structural checks"""

    is_valid, errors = CodeValidator.validate(
        generated_files=state["generated_files"],
        expected_files=state["file_group"]["files"]
    )
    print(f"ERRORS: {errors}")
    return {
        "is_valid": is_valid,
        "errors": errors
    }

def correct_code(state: Dict) -> Dict:
    """NODE 4: Self-correct based on validation errors."""

    retry_num = state["retry_count"] + 1
    prompt = _build_correct_code_prompt(state)
    generated_files, reasoning = _generate_code(prompt)

    return {
        "generated_files": generated_files,
        "reasoning": reasoning,
        "retry_count": retry_num
    }

def _build_generate_code_prompt(state: Dict) -> str:
    """Build the code generation prompt"""

    file_group = state["file_group"]
    files_section = ""

    # Create File Section Sub-Prompt
    for file in file_group["files"]:

        files_section += f"\n{'='*60}\n"
        files_section += f"File: {file['file_path']}\n"
        files_section += f"Action: {file['action']}\n"
        files_section += f"Changes needed: {file['changes']}\n"
        files_section += f"Reason: {file['reason']}\n"

        if file["content"]:
            files_section += f"\nCurrent content:\n```\n{file['content']}\n```\n"
        else:
            files_section += "\n(New file - create from scratch)\n"
    
    # Build complete prompt
    prompt = f"""Generate code for these files.

        **Overall Strategy (from planning):**
        {state['understanding']}

        **This Group's Specific Task:**
        {file_group['description']}

        **Issue Context:**
        {state['issue']}

        **Files to Generate:**
        {files_section}

        **CRITICAL INSTRUCTIONS:**

        1. **Completeness:** 
        Return COMPLETE file contents, not just snippets or changes.

        2. **Consistency:** 
        These files are related. Ensure changes are consistent across all files.

        3. **Code Quality:**
        - Follow existing code style (indentation, spacing, naming conventions)
        - Use the same patterns as existing code
        - Add comments for complex logic
        - Ensure valid syntax

        4. **Dependencies & Imports:**
        - Add all necessary imports
        - Remove unused imports
        - Define new properties/fields according to existing code patterns
        - Ensure consistency when files reference each other

        5. **Preserve Existing Functionality:**
        - Do not remove or break existing features unless explicitly instructed
        - Maintain all existing props, functions, exports, and event handlers
        - Only modify what's specified in "Changes needed"

        6. **Conflict Resolution:**
        If a specific file instruction contradicts the Overall Strategy, 
        prioritize the Overall Strategy while ensuring all files remain functional.

        **OUTPUT FORMAT:**
        You MUST use the return_generated_files tool to return all {len(file_group['files'])} files.
        Each file must have:
        - path: The exact file path from above
        - content: The complete file content

        Generate all files now using the tool generate_code.
    """

    return prompt

def _build_correct_code_prompt(state: Dict) -> str:
    """Build the code correction prompt"""
    
    # Aggregate errors from validations
    errors_text = "\n".join(f"- {error}" for error in state["errors"])

    # Aggregate previously generated files for context
    previous_files = ""
    for file in state["generated_files"]:
        previous_files += f"\n --- {file['path']} --- \n{file['content']}"
    
    # Build complete prompt
    prompt = f"""

    Fix these validation errors in your previous code generation.

    **Errors Found:**
    {errors_text}

    **Your Previous Reasoning:**
    {state['reasoning']}

    **Your Previous Files:**
    {previous_files}

    **Instructions:**
    - Fix the specific errors listed above
    - Ensure all files are complete and valid
    - Maintain consistency across files

    Use the generate_code tool to return corrected files.

    """

    return prompt

def _generate_code(prompt: str) -> Tuple[List[Dict], str]:
    """Generate the code based on instruction from the Planner"""
    
    tools = [
        {
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
    ]

    # Call Claude with tool use
    client = Anthropic(api_key=settings.CLAUDE_API_KEY.get_secret_value())
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        temperature=0,
        tools=tools,
        tool_choice={"type": "tool", "name": "generate_code"},
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract content
    tool_use = next(
        (block for block in response.content if block.type == "tool_use"),
        None
    )

    if not tool_use:
        return [], "" 
    
    generated_files = tool_use.input.get("files",[])
    reasoning = tool_use.input.get("reasoning","")

    return generated_files, reasoning