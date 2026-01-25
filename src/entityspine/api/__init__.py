"""
EntitySpine REST API - FastAPI application for entity resolution.

This module provides a FastAPI-based REST API for EntitySpine.
It exposes the EntityResolver functionality via HTTP endpoints.

Quick Start:
    uvicorn entityspine.api.app:app --reload

Endpoints:
    GET  /health                    - Health check
    GET  /info                      - API information
    GET  /resolve/{query}           - Resolve any identifier
    POST /resolve/batch             - Batch resolution
    GET  /entities/cik/{cik}        - Get entity by CIK
    GET  /entities/ticker/{ticker}  - Get entity by ticker
    GET  /entities/{id}             - Get entity by ID
    GET  /search                    - Search entities

Configuration:
    Environment variables:
        ENTITYSPINE_DB_PATH  - Path to SQLite database
        ENTITYSPINE_AUTO_LOAD_SEC - Auto-load SEC data (default: true)
"""

from entityspine.api.app import app, create_app

__all__ = ["app", "create_app"]
