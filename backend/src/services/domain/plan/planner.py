import json
import logging

from litellm import completion, completion_cost

from core.config import settings
from schemas.response.agents.context import ContextAssemblerResponse

logger = logging.getLogger(__name__)

class PlannerAgent:
    """Creates execution plan with file grouping and retry logic"""

    def __init__(self, model: str = None, temperature: float = 0.0):
        self.model = model or "claude-sonnet-4-20250514"
        self.temperature = temperature
        
    def create_plan(self, context: ContextAssemblerResponse) -> dict:
        """
        Orchestrates a two-stage agentic workflow to generate and refine a code execution plan.

        This method implements a 'Reflexion' pattern:
        1.  **Generation Phase**: Instructs Claude to create an initial plan using the 
            `create_execution_plan` tool based on the provided issue and file context.
        2.  **Validation Phase**: Sends the initial plan back to the model with a 
            critique prompt to check for circular dependencies, missing imports, 
            and logic errors.
        3.  **Finalization**: Extracts and returns the most refined version of the plan 
            after the reflection turn.

        Args:
            context (ContextAssemblerResponse): A structured object containing the 
                target GitHub issue details and a list of semantically relevant 
                files (with summaries, signatures, and imports).

        Returns:
            dict: The validated execution plan containing 'understanding', 'file_groups', 
                and 'execution_order'.
        """

        messages = []

        # Create initial plan
        messages.append({
            "role": "user",
            "content": self._build_creation_prompt(context)
        })

        response = completion(
            model=self.model,                    
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                *messages
            ],
            temperature=self.temperature,       
            tools=self._get_tool_schema(),
            tool_choice={                                         
                "type": "function",
                "function": {"name": "create_execution_plan"}
    }
        )
    
        initial_plan = self._extract_plan(response)
        tool_use_id = self._extract_tool_use_id(response)
        
        # Review initial plan
        messages.extend([
            {
                "role": "assistant",
                "content": None,
                "tool_calls": response.choices[0].message.tool_calls
            },
            {
                "role": "tool",
                "tool_call_id": tool_use_id,
                "content": "Plan created successfully."
            },
            {
                "role": "user",
                "content": self._build_reflection_prompt()
            }
        ])

        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                *messages
            ],
            temperature=self.temperature,
            tools=self._get_tool_schema(),
            tool_choice="auto"
        )
        
        reflected_plan: dict = self._extract_plan(response)
        
        if reflected_plan:
            return reflected_plan  
        else:
            return initial_plan
    
    def _get_system_prompt(self) -> str:
        return """

            You are an AI planner for an autonomous coding agent.

            Your job: Create a minimal, focused execution plan to resolve the GitHub issue.

            ## Planning Guidelines

            1. **Filter ruthlessly**: Only include files that directly need changes
            - Exclude: context files, unrelated files, files in wrong layer
            - Include: Only files that must change to solve the issue

            2. **Start simple**: Prefer fewer files over more
            - Good: 1-2 files
            - Acceptable: 3-4 files
            - Red flag: 5+ files (probably over-engineering)

            3. **Group related files**: Files that work together go in same group
            - Same component/feature → same group
            - Independent changes → separate groups

            4. **Order by dependencies**: Process dependencies before dependents
            - Base/utility files first
            - Components that use them second

            ## Critical: Exact Field Names

            Each file MUST use this exact structure:
            ```json
            {
            "file_path": "path/to/file.tsx",     // NOT "path", "filepath", or "filename"
            "action": "modify",                   // "create" | "modify" | "delete"
            "changes": "specific changes needed"  // NOT "description" or "summary"
            }
            ```

            ## Example Plans

            ### GOOD Plan
            Issue: "Add color prop to Node component"
            ```json
            {
            "understanding": "Add color prop to Node component to allow customization",
            "file_groups": [
                {
                "group_id": "add-color-prop",
                "description": "Add color prop to Node component",
                "files": [
                    {
                    "file_path": "src/components/Node.tsx",
                    "action": "modify",
                    "changes": "Add color prop to interface and apply to node styling"
                    }
                ]
                }
            ],
            "execution_order": ["add-color-prop"]
            }
            ```

            Why good: Minimal (1 file), specific changes, correct field names

            ### BAD Plan
            ```json
            {
            "file_groups": [
                {
                "files": [
                    "Node.tsx",
                    "NodeContainer.tsx", 
                    "index.ts",
                    "types.ts"
                ]
                }
            ]
            }
            ```

            Why bad:
            - Files as strings (should be objects)
            - Missing required fields (file_path, action, changes)
            - Too many files (over-engineered)
            - No group_id or description

            ### BAD Plan
            ```json
            {
            "file_groups": [
                {
                "group_id": "ui-changes",
                "files": [
                    {
                    "path": "src/Button.tsx",           // Wrong: should be "file_path"
                    "type": "modify",                   // Wrong: should be "action"
                    "description": "Add color support"  // Wrong: should be "changes"
                    }
                ]
                }
            ]
            }
            ```

            Why bad: Wrong field names (path/type/description instead of file_path/action/changes)

            ## Rules

            - **Conservative scope**: When in doubt, exclude the file
            - **Specific changes**: "Add color prop to interface" not "Update component"
            - **No test files**: Unless issue explicitly asks for tests
            - **No config files**: Unless issue explicitly asks for config changes
            - **No documentation**: Unless issue explicitly asks for docs

            ## Plan Structure

            Required fields:
            - `understanding`: Brief analysis (1-2 sentences)
            - `file_groups`: Array of file groups
            - `group_id`: Unique identifier (e.g., "add-feature-x")
            - `description`: What this group accomplishes
            - `files`: Array of file objects with exact field names above
            - `execution_order`: Array of group_ids in processing order

            Use the create_plan tool to return your execution plan.
        """

    def _build_creation_prompt(self, context) -> str:
        """Build initial creation prompt"""

        # Build context for files
        issue = context["issue"]
        files = context["files"]
        
        files_text = ""
        for file in files:
            files_text += f"\n### {file["file_path"]}\n"
            files_text += f"Summary: {file["summary"]}\n"
            files_text += f"Signatures: {file["signatures"]}\n"
            files_text += f"Imports: {file["imports"]}"

        return f"""

            Create an execution plan for this issue.

            **Issue:**
            {issue['query']}

            **Existing Files (from search - for Job 1 - Execution Plan):**
            {files_text}

            **Your Job:**
            
            1. Analyze the existing files and create a minimal execution plan.
            - Filter to only essential files
            - Group by dependencies
            - Specify exact changes needed
            
            Use create_execution_plan tool.

        """
    
    def _build_reflection_prompt(self) -> str:

        return """
        
            Review your plan:

            - Files that import each other in same group?
            - Circular dependencies?
            - Execution order correct?
            - All files essential (not "nice to have")?

            If issues: Use create_execution_plan again.
            If good: Reply "Plan is sound."
        """
        
    def _get_tool_schema(self) -> list:
        """Tool schema for creating execution plan"""

        return [
        {
            "type": "function",  
            "function": {        
                "name": "create_execution_plan",
                "description": "Create execution plan with file grouping",
                "parameters": {  
                    "type": "object",
                    "properties": {
                        "understanding": {"type": "string"},
                        "file_groups": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "group_id": {
                                        "type": "string",
                                        "description": "REQUIRED: Unique identifier for this group (e.g., 'add-color-prop'). Use snake_case."
                                    },
                                    "description": {"type": "string"},
                                    "files": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "file_path": {"type": "string"},
                                                "action": {"type": "string", "enum": ["modify", "create"]},
                                                "changes": {"type": "string"},
                                                "reason": {"type": "string"}
                                            },
                                            "required": ["file_path", "action", "changes", "reason"]
                                        }
                                    },
                                    "dependencies": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["group_id", "description", "files", "dependencies"]
                            }
                        },
                        "execution_order": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["understanding", "file_groups", "execution_order"]
                }
            }  
        }
    ]
    
    def _extract_plan(self, response) -> dict:
        """Extracts plan from tool use"""

        try:
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "create_execution_plan":
                        return json.loads(tool_call.function.arguments)
            return None
        except Exception as e:
            logger.error(f"Failed to extract plan: {e}")
            return None
    
    def _extract_tool_use_id(self, response) -> str:
        """Extracts the tool_use ID associated with a tool call to ensure conversation integrity"""

        try:
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                return message.tool_calls[0].id
            return None
        except Exception as e:
            logger.error(f"Failed to extract tool ID: {e}")
            return None