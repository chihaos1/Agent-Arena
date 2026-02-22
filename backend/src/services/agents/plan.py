from anthropic import Anthropic

from core.config import settings
from schemas.response.agents.context import ContextAssemblerResponse

class PlannerAgent:
    """Creates execution plan with file grouping and retry logic"""

    def __init__(self):
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY.get_secret_value())

    def create_plan(self, context: ContextAssemblerResponse):
        """
        Docstring for create_plan
        
        :param self: Description
        :param context: Description
        :type context: ContextAssemblerResponse
        """

        print(self._build_creation_prompt(context))
    
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

            Create an execution plan for this GitHub issue.

            **Issue:**
            Title: {issue['query']}

            **Relevant Files:**
            {files_text}

            **Grouping Rules:**
            1. Files that depend on each other → SAME group (one Coder agent sees all)
            2. Independent files → DIFFERENT groups (can parallelize)
            3. Each group gets ONE Coder agent with access to ALL files in that group

            **Examples:**
            - Good: [ThemeContext.tsx, ThemeToggle.tsx, Header.tsx] in one group
            (ThemeToggle imports ThemeContext, Header imports ThemeToggle)
            
            - Bad: Each file in separate group
            (Can't see each other, will be inconsistent!)

            Use the create_execution_plan tool.
        """
        