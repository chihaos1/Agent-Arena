import pathlib
import os
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings

load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent / ".env")

class Settings(BaseSettings):
    """Contains the configuration settings for the application"""

    # Core Settings
    @property
    def CORS_ORIGINS(self) -> List[str]:
        cors_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        return [origin.strip() for origin in cors_str.split(',') if origin.strip()]
    ENVIRONMENT: Literal["DEV","PREPROD","PROD"] = os.getenv("ENVIRONMENT")

    # Project Settings
    PROJECT_NAME: str = "AutoDev"
    API_VERSION: str = os.getenv("API_VERSION")

    # Claude Settings
    # CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY")
    # CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL")
    # CLAUDE_MAX_TOKENS: int = os.getenv("CLAUDE_MAX_TOKENS")

    # OpenAI Settings
    OPENAI_API_KEY: SecretStr = os.getenv("OPENAI_API_KEY")

    # Pinecone Settings
    PINECONE_API_KEY: SecretStr = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME")

settings: Settings = Settings()