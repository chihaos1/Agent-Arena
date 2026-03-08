from core.logging import setup_logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.repo import token, issue, embed
from api.v1.agents import context, plan, orchestrate
from core.config import settings

load_dotenv()
setup_logging()

app = FastAPI(
    title = settings.PROJECT_NAME,
    version = settings.API_VERSION, 
    docs_url = None if settings.ENVIRONMENT == "PROD" else "/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = settings.CORS_ORIGINS,
    allow_methods = ["*"],
    allow_headers = ["*"],
    allow_credentials = True
)

# Repo Routes
app.include_router(token.router)
app.include_router(issue.router)
app.include_router(embed.router)

# Agent Routes
app.include_router(context.router)
app.include_router(plan.router)
app.include_router(orchestrate.router)

@app.get("/")
async def root():
    return {
        "message": f"{settings.PROJECT_NAME} API"
    }