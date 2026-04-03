import requests
from fastapi import APIRouter, HTTPException

from core.config import settings
from schemas.request.repo.create_issue import CreateIssueRequest

router = APIRouter(prefix="/insights", tags=["insights"])

@router.get("/events")
async def get_insights_events():
    """
    Fetches $ai_generation events from PostHog for LLM cost and token analytics.

    Returns:
        Raw PostHog events response with results array.

    Raises:
        HTTPException: If the PostHog API request fails.
    """

    posthog_key = settings.POSTHOG_PERSONAL_API_KEY.get_secret_value()
    response = requests.get(
        f"https://app.posthog.com/api/projects/{settings.POSTHOG_PROJECT_ID}/events/?event=%24ai_generation&limit=1000",
        headers={"Authorization": f"Bearer {posthog_key}"}
    )

    if not response.ok:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch PostHog events")

    return response.json()