# from fastapi import APIRouter, HTTPException
# from github import GithubException

# from schemas.request.agents.context import SearchContextRequest
# from schemas.response.agents.context import ContextAssemblerResponse
# from services.agents.context.assemble import ContextAssembler

# router = APIRouter(prefix="/agents", tags=["agents"])

# @router.post("/generate-code", response_model=ContextAssemblerResponse)
# async def generate_code(request: SearchContextRequest):
#     """

#     """

#     try: 

#         return ContextAssemblerResponse(
#             issue=context["issue"],
#             repo_context=context["repo_context"],
#             files=context["files"]
#         )
    

#     except GithubException as e:
#         if e.status == 401:
#             raise HTTPException(status_code=401, detail="Invalid Github token")
#         elif e.status == 404:
#             raise HTTPException(status_code=404, detail=f"Repository {request.repo_name} was not found or no permission to access")
#         else:
#             raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")