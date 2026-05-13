"""
OpenManus API Service.

Production-ready REST API with SSE streaming.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import api_config
from api.core.events import event_bus
from api.models import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    event_bus.connect()
    
    # Ensure workspace directories exist
    api_config.storage.base_path.mkdir(parents=True, exist_ok=True)
    api_config.storage.log_path.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown
    event_bus.disconnect()


app = FastAPI(
    title=api_config.api.title,
    version=api_config.api.version,
    description=api_config.api.description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message=str(exc),
        ).model_dump(),
    )


# Import and include routers
from api.routes import admin, health, tasks

app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": api_config.api.title,
        "version": api_config.api.version,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=api_config.api.host,
        port=api_config.api.port,
        reload=api_config.api.debug,
        workers=1,
    )