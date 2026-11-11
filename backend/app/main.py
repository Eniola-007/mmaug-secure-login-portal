from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import agents, audit, authentication, dashboard, health, users
from app.runtime_migrations import start_runtime_migration


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    start_runtime_migration(settings.environment)
    yield


app = FastAPI(
    title="MMAUG High School Secure Login API",
    version="0.1.0",
    docs_url="/docs" if get_settings().environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "X-Dev-User"],
)

app.include_router(health.router)
app.include_router(authentication.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
