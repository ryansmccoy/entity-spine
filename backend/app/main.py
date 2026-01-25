"""
Entity Spine Backend - Main FastAPI Application
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.db.session import engine, create_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - startup and shutdown events."""
    # Startup
    setup_logging()
    await create_tables()
    yield
    # Shutdown
    await engine.dispose()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="""
        Entity Spine API - Financial Data & Knowledge Graph Platform
        
        ## Features
        
        - **Company Profiles**: Comprehensive company data with financial metrics
        - **SEC Filings**: Search, browse, and analyze SEC filings
        - **Knowledge Graph**: Entity extraction and relationship mapping
        - **Financial Data**: Structured financial statements and XBRL facts
        - **Search**: Universal search across companies, filings, and entities
        - **Watchlists**: Track companies and receive alerts
        
        ## Authentication
        
        Most endpoints require authentication. Use the `/auth/token` endpoint
        to obtain a JWT token, then include it in the `Authorization` header:
        
        ```
        Authorization: Bearer <your-token>
        ```
        """,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Check API health status."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
        }
    
    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
