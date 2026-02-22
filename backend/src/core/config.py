import pathlib
import os
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# load_dotenv(dotenv_path=pathlib.Path(__file__).parent.parent / ".env")

class Settings(BaseSettings):
    """Contains the configuration settings for the application"""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Settings
    # @property
    # def CORS_ORIGINS(self) -> List[str]:
    #     cors_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    #     return [origin.strip() for origin in cors_str.split(',') if origin.strip()]
    ENVIRONMENT: Literal["DEV","PREPROD","PROD"] = "DEV"
    CORS_ORIGINS_RAW: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(',') if origin.strip()]

    # Project Settings
    PROJECT_NAME: str = "AutoDev"
    API_VERSION: str = "v1"

    # Claude Settings
    CLAUDE_API_KEY: SecretStr
    # CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL")
    # CLAUDE_MAX_TOKENS: int = os.getenv("CLAUDE_MAX_TOKENS")

    # OpenAI Settings
    OPENAI_API_KEY: SecretStr

    # Pinecone Settings
    PINECONE_API_KEY: SecretStr
    PINECONE_INDEX_NAME: str

settings: Settings = Settings()