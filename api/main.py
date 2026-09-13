import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import leads, runs
from api.schemas import HealthCheckResponse
from config.settings import get_settings

logger = logging.getLogger("tvb_agent.api")


def create_app() -> FastAPI:
    """FastAPI application factory for the TVB Autonomous Lead Discovery API."""
    settings = get_settings()

    app = FastAPI(
        title="TVB Autonomous Lead Discovery API",
        description="REST API layer exposing autonomous lead discovery, research, deterministic qualification, and email verification.",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # CORS configuration for React Frontend
    origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API Routers
    app.include_router(runs.router)
    app.include_router(leads.router)

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled API error on '{request.url}': {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred while processing the request."},
        )

    # Health Check Endpoint
    @app.get("/api/health", response_model=HealthCheckResponse, tags=["Health"])
    def health_check():
        """Health check endpoint confirming API availability."""
        return HealthCheckResponse(status="ok", version="1.0.0")

    return app


app = create_app()
