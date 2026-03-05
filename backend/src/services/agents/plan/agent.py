from anthropic import Anthropic
from anthropic.types import Message

from core.config import settings
from schemas.response.agents.context import ContextAssemblerResponse

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

        reflected_plan: dict = self._extract_plan(response)

        return reflected_plan
    
    def _get_system_prompt(self) -> str:
        return """

            You are an AI planner with two primary responsibilities:

            **Job 1 - Architect:** Create a minimal, dependency-aware execution plan to resolve the GitHub issue.
            **Job 2 - DevOps:** Configure the sandbox environment (runtimes and commands) based on repository manifests to ensure the plan can be verified.

            ---

            ## JOB 1: EXECUTION PLAN (Code Architecture)

            **Instructions:**

            1. **Filter ruthlessly**: Only include files that need changes. Exclude context files, wrong layer, unrelated files.
            2. **Start simple**: Include only essential files. Avoid "nice to have" additions. Prefer 2-4 files over 6+ files.
            3. **Group dependencies**: Files that import each other → same group. Independent → separate groups.
            4. **Order by dependencies**: Base files before dependents.

            **Important:** Manifests (package.json, requirements.txt) are for Job 2 (sandbox config), NOT for Job 1 (file changes).
            Do NOT include manifest files in your file_groups unless the issue specifically asks to modify them.

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

            ---

            ## JOB 2: SANDBOX CONFIGURATION (Testing Environment)

            **Runtime Detection from Manifests:**
            
            - `package.json` found → Runtime: "node"
            - Look for lockfile signals: `yarn.lock` → Use `yarn install` and `yarn build`
            - Look for lockfile signals: `pnpm-lock.yaml` → Use `pnpm install` and `pnpm build`
            - No lockfile → Use `npm install` and `npm run build`
            - Check `"scripts"` section for actual test command
            
            - `requirements.txt` OR `pyproject.toml` → Runtime: "python"
            - If `pyproject.toml` contains `[tool.poetry]` → Use `poetry install` and `poetry run pytest`
            - Otherwise → Use `pip install -e .` and `pytest`
            
            - `go.mod` → Runtime: "go"
            - Setup: `go mod download`
            - Tests: `go test ./...`
            
            - Multiple manifests → Multiple runtimes (polyglot project)

            **Smart Command Pruning (Critical for Efficiency):**
            
            Look at the file extensions in your execution plan to determine which test suites to run:
            - If ONLY `.ts`/`.tsx`/`.js`/`.jsx` files modified → Only run Node.js build
            - If ONLY `.py` files modified → Only run Python tests
            - If ONLY `.go` files modified → Only run Go tests
            - If files from multiple languages modified → Run all relevant test suites

            **Test Command Guidelines:**
            - For Node.js projects: Use `npm run build` to validate TypeScript compilation
            - For Python projects: Use `pytest` to run tests
            - For Go projects: Use `go test ./...`
            - Build catches: TypeScript errors, import issues, syntax problems
            - Tests catch: Logic errors, edge cases, integration issues

            **Manifest Interpretation:**
            - If a manifest is listed but its content is not shown, assume it contains standard dependencies.
            - Do NOT guess specific version numbers unless they are visible in the provided snippets.
            - Focus on lockfile signals (yarn.lock, pnpm-lock.yaml) to choose the correct package manager.

            **Monorepo Handling:**
            - If manifests exist in subdirectories (e.g., `frontend/package.json`, `backend/pyproject.toml`), detect the monorepo structure.
            - Commands should run from the appropriate subdirectory or use monorepo tools if detected.

            ---

            Use create_execution_plan tool. Focus on:
            - Job 1: Minimal files that solve the immediate issue
            - Job 2: Correct sandbox runtimes and commands based on manifests and modified file types

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

        # Build context for manifests
        manifests = context.get("manifests", {})

        manifests_text = ""
        if manifests:
            manifests_text = "\n\n**Project Manifests:**\n"
            manifests_text += "Found: " + ", ".join(manifests.keys()) + "\n"

            # Include full content for key manifests only
            key_manifests = ['package.json', 'pyproject.toml', 'go.mod', 'Cargo.toml']
            for path, content in manifests.items():
                if any(key in path for key in key_manifests):
                    display_content = content[:500] + "\n... [TRUNCATED] ...\n" if len(content) > 500 else content
                    manifests_text += f"\n### {path}\n```\n{display_content}\n```\n"

        return f"""

            Create an execution plan for this issue.

            **Issue:**
            {issue['query']}

            **Existing Files (from search - for Job 1 - Execution Plan):**
            {files_text}

            **Existing Manifests (from search - for Job 2 - Sandbox Configurations):**
            {manifests_text}

            **Your Two Jobs:**
            
            1. **Job 1 (Architect):** Analyze the existing files and create a minimal execution plan.
            - Filter to only essential files
            - Group by dependencies
            - Specify exact changes needed
            
            2. **Job 2 (DevOps):** Analyze the manifests and configure the sandbox.
            - Detect runtimes from manifests
            - Generate setup commands
            - Generate test commands with smart pruning (only test modified file types)

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
                        "execution_order": {"type": "array", "items": {"type": "string"}},
                        "sandbox_config": {
                            "type": "object",
                            "description": "Configuration for sandbox testing environment",
                            "properties": {
                                "runtimes": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Detected runtimes (e.g., ['node', 'python'])"
                                },
                                "setup_commands": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Commands to set up environment (e.g., ['npm install', 'pip install -e .'])"
                                },
                                "test_commands": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Commands to run tests (e.g., ['npm test', 'pytest']). Use smart pruning."
                                }
                            },
                            "required": ["runtimes", "setup_commands", "test_commands"]
                        }
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