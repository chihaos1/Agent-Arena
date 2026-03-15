"""
PostHog Observability Client

For tracking agent events in PostHog.
"""

import logging
from posthog import Posthog
from core.config import settings

logger = logging.getLogger(__name__)

class PostHogClient:
    """PostHog client for agent observability"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize PostHog client"""

        api_key = settings.POSTHOG_API_KEY.get_secret_value()
        host = settings.POSTHOG_HOST

        if not api_key:
            logger.warning("PostHog API key not found. Event tracking disabled.")
            self.client = None
            self.enabled = False
            return
        
        self.client = Posthog(
            project_api_key=api_key,
            host=host
        )

        self.enabled = True
        logger.info(f"PostHog client initialized: {host}")

    def capture(self, distinct_id: str, event: str, properties: dict = None):
        """
        Capture event in PostHog
        
        Args:
            distinct_id: Unique identifier (use session_id for agents)
            event: Event name (e.g., 'agent_run_started')
            properties: Event properties dict
        """

        if not self.enabled:
            logger.debug(f"PostHog disabled. Would track: {event}")
            return
        
        try: 
            self.client.capture(
                distinct_id=distinct_id,
                event=event,
                properties=properties or {}
            )

        except Exception as e:
            logger.error(f"PostHog capture failed: {e}")

    def shutdown(self):
        """Flush and close PostHog client"""
        if self.enabled and self.client:
            self.client.shutdown()

posthog = PostHogClient()