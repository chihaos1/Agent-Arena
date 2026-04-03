import requests
from fastapi import APIRouter, HTTPException

from core.config import settings
from schemas.request.repo.create_issue import CreateIssueRequest

router = APIRouter(prefix="/insights", tags=["insights"])

@router.get("/funnel")
async def get_funnel():
    """
    Fetches phase funnel insight from PostHog.

    Returns:
        PostHog insight response with funnel result data.

    Raises:
        HTTPException: If the PostHog API request fails.
    """

    posthog_key = settings.POSTHOG_PERSONAL_API_KEY.get_secret_value()
    response = requests.get(
        f"https://app.posthog.com/api/projects/{settings.POSTHOG_PROJECT_ID}/insights/{settings.POSTHOG_FUNNEL_INSIGHT_ID}",
        headers={"Authorization": f"Bearer {posthog_key}"}
    )

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch funnel data")

    return response.json()