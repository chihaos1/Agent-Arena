from pydantic import BaseModel

from schemas.response.agents.context import ContextAssemblerResponse

class ExecutionPlanRequest(BaseModel):
    context: ContextAssemblerResponse
