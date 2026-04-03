from core.logging import setup_logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.agents import context, plan, orchestrate
from api.v1.arena import arena
from api.v1.insights import llm, funnel
from api.v1.repo import token, embed, create_issue, repo_preview
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

# Agent Routes
app.include_router(context.router)
app.include_router(plan.router)
app.include_router(orchestrate.router)

# Arena Route
app.include_router(arena.router)

# Insights Route
app.include_router(llm.router)
app.include_router(funnel.router)

# Repo Routes
app.include_router(token.router)
app.include_router(embed.router)
app.include_router(create_issue.router)
app.include_router(repo_preview.router)

@app.get("/")
async def root():
    return {
        "message": f"{settings.PROJECT_NAME} API"
    }