from pydantic import BaseModel

class ValidateTokenRequest(BaseModel):
    """Request to validate user-provided GitHub Token"""

    github_token: str
    repo_name: str

class ValidateTokenResponse(BaseModel):
    """Response from validating user-provided GitHub Token"""

    success: bool
    repo_name: str
    repo_url: str
    total_files: int
    message: str