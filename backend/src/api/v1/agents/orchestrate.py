import logging
import uuid
from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.agents.orchestrate import OrchestrateRequest
from schemas.response.agents.orchestrate import OrchestrateResponse
from services.graph.state import create_initial_state
from services.graph.builder import build_graph
# from services.agents.context.agent import ContextAssembler
# from services.agents.plan.agent import PlannerAgent
# from tasks.orchestrate import orchestrate_workflow
# from tasks.state import create_workflow_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest):
    """
    Start AutoDev ReAct workflow.
    
    Flow:
    1. Create initial state from request
    2. Build graph with tools
    3. Invoke graph
    4. Return result
    """

    try:

        session_id = str(uuid.uuid4())
        logger.info(f"Starting AutoDev workflow: session={session_id}, repo={request.repo_name}")

        # 1. Create initial state
        state = create_initial_state(
            issue_id=session_id,  # Or use actual GitHub issue ID if available
            issue_description=request.query,
            repo_name=request.repo_name,
            branch_name="main",  # Or from request
            user_id="api_user",  # Or from auth context
            session_id=session_id,
            llm_model="claude-sonnet-4-20250514"
        )

        # 2. Build graph with GitHub token
        graph = build_graph(
            github_token=request.github_token.get_secret_value(),
            enable_checkpointing=True
        )

        logger.info(f"Graph built for session {session_id}")

        # 3. Run graph
        config = {"configurable": {"thread_id": session_id}}
        result = graph.invoke(state, config)

        logger.info(
            f"Workflow completed: session={session_id}, "
            f"final_step={result['current_step']}, "
            f"messages={len(result['messages'])}",
        )

        return OrchestrateResponse(
            workflow_id=session_id,
            status=result["current_step"],
            pr_url=result.get("pr_url"),
            files_modified=len(result.get("files_to_modify", [])),
            cost_usd=result.get("estimated_cost_usd", 0.0)
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





# """
#     Start an AI-powered code generation workflow.
    
#     Flow:
#     1. Run Context Assembler (finds relevant files)
#     2. Run Planner Agent (creates execution plan)
#     3. Create workflow state in Redis
#     4. Trigger Celery orchestrator to dispatch the coding agent
    
#     User polls /status/{workflow_id} to check progress.
#     """

#     try: 
        
#         # 1. Organize the context with Assembler (passes context to Planner)
#         assembler = ContextAssembler(
#             github_token=request.github_token.get_secret_value()
#         )

#         context = assembler.assemble_context(
#             query=request.query, 
#             repo_name=request.repo_name
#         )

#         logger.info(f"Context fetched: {context}")

#         # # 2. Create and review execution plan with Planner (passes execution plan to Planner)
#         # planner = PlannerAgent()
#         # execution_plan: dict = planner.create_plan(context)

#         # logger.info(f"Execution Plan generated: {execution_plan}")

#         # execution_plan = {'understanding': 'The issue requires adding the ability for nodes to change colors. Looking at the existing Node.tsx component, I can see it currently has a hardcoded color "#C5C2A8" for the mesh material and uses a `color` prop for the line material. To implement color changing functionality, I need to:\n\n1. Add a color picker UI component to allow users to select colors\n2. Modify the Node component to accept and use dynamic colors\n3. Update the GraphNode model to include a color property\n4. Integrate the color picker into the node interaction flow\n\nThe minimal approach focuses on the core functionality: a color picker component and modifications to the existing Node component to support dynamic colors.', 'file_groups': [{'group_id': 'data-model-update', 'description': 'Update GraphNode model to support color property', 'files': [{'file_path': 'frontend/src/models/Graph.ts', 'action': 'modify', 'changes': 'Add optional color property to GraphNode interface with default color value.', 'reason': 'Need to extend the data model to store node colors - this is the foundation that other components depend on'}], 'dependencies': [], 'can_parallelize': True}, {'group_id': 'color-picker-and-node', 'description': 'Create color picker component and integrate with Node component', 'files': [{'file_path': 'frontend/src/components/ui/ColorPicker/ColorPicker.tsx', 'action': 'create', 'changes': 'Create a color picker component with predefined color palette and custom color input. Include props for current color, onChange callback, and visibility control.', 'reason': 'Need a UI component to allow users to select colors for nodes'}, {'file_path': 'frontend/src/components/ui/ColorPicker/ColorPicker.css', 'action': 'create', 'changes': 'Add styling for color picker component including color palette grid, color swatches, and custom color input field.', 'reason': 'Styling needed for the color picker component'}, {'file_path': 'frontend/src/components/3d/graph/Node.tsx', 'action': 'modify', 'changes': "Import ColorPicker component, add color state management, update mesh materials to use dynamic color from node.color property instead of hardcoded '#C5C2A8', add right-click context menu or double-click handler to show color picker.", 'reason': 'Core component that needs to support color changing functionality and imports the ColorPicker'}], 'dependencies': ['data-model-update'], 'can_parallelize': False}], 'execution_order': ['data-model-update', 'color-picker-and-node'], 'sandbox_config': {'runtimes': ['python', 'node'], 'setup_commands': ['cd backend && pip install -e .', 'cd frontend && npm install'], 'test_commands': ['cd frontend && npm run build']}}

#         # # 3. Execute the execution plan with Coder
#         # workflow_id = str(uuid.uuid4())
        
#         # create_workflow_state(
#         #     workflow_id=workflow_id,
#         #     execution_plan=execution_plan,
#         #     issue_description=request.query,
#         #     repo_name=request.repo_name,
#         #     github_token=request.github_token.get_secret_value()
#         # )
#         # logger.info(f"Current Workflow ID: {workflow_id}")

#         # orchestrate_workflow.delay(workflow_id)
#         # logger.info(f"Workflow {workflow_id} started")
