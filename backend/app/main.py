"""
Trading-FAIT Backend
FastAPI Application with WebSocket support for AI Trading Agents
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import get_logger, configure_logging
from app.api.websocket import websocket_endpoint
from app.services.market_data import get_market_data_service

# Initialize logging
configure_logging()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    settings = get_settings()
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        azure_configured=settings.is_configured,
    )
    yield
    # Cleanup on shutdown
    market_service = get_market_data_service()
    await market_service.close()
    logger.info("application_shutdown")


# Get settings
settings = get_settings()

app = FastAPI(
    title="Trading-FAIT API",
    description="AI-Agenten Trading-Webapp mit Magentic-One + Azure OpenAI",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS Configuration for Frontend
# Allow all origins for WebSocket in development (Codespaces, local, Docker)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for WebSocket compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Trading-FAIT Backend",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    settings = get_settings()
    return {
        "status": "healthy",
        "components": {
            "api": "ok",
            "azure_openai": "configured" if settings.is_configured else "not_configured",
            "agents": "ready",
            "market_data": "ready",
            "websocket": "ready",
        },
    }


@app.get("/config/status")
async def config_status():
    """Check configuration status (no secrets exposed)"""
    settings = get_settings()
    return {
        "azure_openai_configured": settings.is_configured,
        "azure_openai_endpoint": settings.azure_openai_endpoint[:30] + "..." if settings.is_configured else "not_set",
        "azure_openai_deployment": settings.azure_openai_deployment,
        "log_level": settings.log_level,
        "agent_max_turns": settings.agent_max_turns,
        "agent_max_stalls": settings.agent_max_stalls,
    }


@app.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get a quick price quote for a symbol"""
    market_service = get_market_data_service()
    return await market_service.get_quick_quote(symbol)


# WebSocket endpoint for real-time agent communication
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time trading queries"""
    await websocket_endpoint(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
