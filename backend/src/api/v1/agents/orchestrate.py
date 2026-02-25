from fastapi import APIRouter, HTTPException
from github import Github, Auth, GithubException
from github.Repository import Repository

from schemas.response.agents.context import ContextAssemblerResponse
from schemas.request.agents.orchestrate import OrchestrateRequest
from schemas.response.agents.orchestrate import OrchestrateResponse
from schemas.response.agents.plan import ExecutionPlanResponse
from services.agents.code.agent import CoderAgent
from services.agents.context.agent import ContextAssembler
from services.agents.plan.agent import PlannerAgent

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest):
    """
    """

    try: 
        
        # Organize the context with Assembler (passes context to Planner)
        # assembler = ContextAssembler(
        #     github_token=request.github_token.get_secret_value()
        # )

        # context: ContextAssemblerResponse = assembler.assemble_context(
        #     query=request.query, 
        #     repo_name=request.repo_name
        # )

        # # Create and review execution plan with Planner (passes execution plan to Planner)
        # planner = PlannerAgent()
        # execution_plan: ExecutionPlanResponse = planner.create_plan(context)


        # -----------------------------
        execution_plan = {
            'understanding': 'The issue requires adding the ability to change node colors. Currently, Node.tsx has hardcoded colors. The most essential approach is to: 1) Add a color property to the node data model, 2) Modify Node.tsx to use dynamic colors from props, and 3) Add a simple color picker in the node detail/edit interface. I should focus on the minimal files needed to make nodes changeable colors work.', 
            'file_groups': [{'group_id': 'node-color-support', 'description': 'Add color support to node data model and rendering', 'files': [{'file_path': 'frontend/src/models/Graph.ts', 'action': 'modify', 'changes': 'Add optional color property to GraphNode interface with default color value', 'reason': 'Need to store color information in the node data structure'}, {'file_path': 'frontend/src/components/3d/graph/Node.tsx', 'action': 'modify', 'changes': "Replace hardcoded color '#C5C2A8' with node.color property, add fallback to default color if not specified", 'reason': 'Core rendering component needs to use dynamic colors from node data'}], 'dependencies': [], 'can_parallelize': False}, {'group_id': 'color-picker-ui', 'description': 'Add color picker interface for node editing', 'files': [{'file_path': 'frontend/src/components/ui/ColorPicker/ColorPicker.tsx', 'action': 'create', 'changes': 'Create simple color picker with predefined color swatches and onChange callback', 'reason': 'Need UI component to allow users to select node colors'}], 'dependencies': ['node-color-support'], 'can_parallelize': True}], 
            'execution_order': ['node-color-support', 'color-picker-ui']}

        # Execute the execution plan with Coder
        github_auth = Auth.Token(request.github_token.get_secret_value())
        github_client = Github(auth=github_auth)
        repo: Repository = github_client.get_repo(request.repo_name) # change to pass token and repo name when using celery

        coder = CoderAgent()
        coder.run(execution_plan["file_groups"][0], execution_plan["understanding"], request.query, repo)

        return OrchestrateResponse(
            query="test"
        )

    except GithubException as e:
        if e.status == 401:
            raise HTTPException(status_code=401, detail="Invalid Github token")
        elif e.status == 404:
            raise HTTPException(status_code=404, detail=f"Repository {request.repo_name} was not found or no permission to access")
        else:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")