from anthropic import Anthropic
from anthropic.types import Message

from core.config import settings
from schemas.response.agents.context import ContextAssemblerResponse
from schemas.response.agents.plan import ExecutionPlanResponse

class PlannerAgent:
    """Creates execution plan with file grouping and retry logic"""

    def __init__(self):
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY.get_secret_value())

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

        response: Message = self.client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            temperature=0,
            system=self._get_system_prompt(),
            tools=self._get_tool_schema(),
            tool_choice = {"type": "tool", "name": "create_execution_plan"},
            messages=messages
        )

        tool_use_id = self._extract_tool_use_id(response)
        
        # Review initial plan
        messages.extend(
            [{
                "role": "assistant",
                "content": response.content
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Plan created successfully."
                    },
                    {
                        "type": "text",
                        "text": self._build_reflection_prompt()
                    }
                ]
            }]
        )

        response: Message = self.client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            temperature=0,
            system=self._get_system_prompt(),
            tools=self._get_tool_schema(),
            tool_choice = {"type": "auto"},
            messages=messages
        )

        reflected_plan: ExecutionPlanResponse = self._extract_plan(response)

        return reflected_plan
    
    def _get_system_prompt(self) -> str:
        return """

            You are an AI code planner creating execution plans for GitHub issues.

            **Instructions:**

            1. **Filter ruthlessly**: Only include files that need changes. Exclude context files, wrong layer, unrelated files.
            2. **Start simple**: Include only essential files. Avoid "nice to have" additions. Prefer 2-4 files over 6+ files.
            3. **Group dependencies**: Files that import each other → same group. Independent → separate groups.
            4. **Order by dependencies**: Base files before dependents.

            **Guidelines:**
            - `can_parallelize: false` → tightly coupled files
            - `can_parallelize: true` → independent changes
            - Be specific in `changes` field
            - If unsure if file is needed, exclude it (can add later)

            **Example:**

            Issue: "Add export to PDF feature"
            Files from search: [ReportViewer.js, PDFService.js, analytics.js, config.json]

            Good plan (focused):
            ```
            file_groups: [
            {{
                group_id: "pdf-export",
                files: [
                {{path: "utils/PDFGenerator.js", action: "create", changes: "PDF generation utility using jsPDF"}},
                {{path: "ReportViewer.js", action: "modify", changes: "Add Export button calling PDFGenerator"}}
                ],
                can_parallelize: false
            }}
            ]
            ```
            Excluded: PDFService.js (backend persistence not needed yet), analytics.js (unrelated), config.json (no changes)

            Bad plan (overengineered):
            ```
            file_groups: [
            {{files: [PDFGenerator.js, ReportViewer.js, PDFService.js, analytics.js, logger.js, config.json]}}
            ]
            ```
            Why bad: Adds analytics tracking, backend persistence, logging before user even tries the feature

            Use create_execution_plan tool. Focus on solving the immediate issue with minimal files.

        """

    def _build_creation_prompt(self, context) -> str:
        """Build initial creation prompt"""

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

            **Existing Files (from search):**
            {files_text}

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
                "name": "create_execution_plan",
                "description": "Create execution plan with file grouping",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "understanding": {"type": "string"},
                        "file_groups": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "group_id": {"type": "string"},
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
                                    "can_parallelize": {"type": "boolean"}
                                },
                                "required": ["group_id", "description", "files", "dependencies", "can_parallelize"]
                            }
                        },
                        "execution_order": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["understanding", "file_groups", "execution_order"]
                }
            }
        ]
    
    def _extract_plan(self, response: Message) -> dict:
        """Extracts plan from tool use"""

        for block in response.content:
            if block.type == "tool_use" and block.name == "create_execution_plan":
                return block.input
        return None
    
    def _extract_tool_use_id(self, response: Message) -> str:
        """Extracts the tool_use ID associated with a tool call to ensure conversation integrity"""

        for block in response.content:
            if block.type == "tool_use":
                return block.id