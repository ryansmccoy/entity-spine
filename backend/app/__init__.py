"""
Entity Spine Backend - FastAPI Application
==========================================

A comprehensive REST API backend for SEC filings analysis, company profiles,
and financial knowledge graph exploration.

Features
--------
- **Companies API**: Search, filter, and retrieve company profiles with financial metrics
- **Filings API**: Browse SEC filings with Instagram-style feed and detailed sections
- **Knowledge Graph API**: Explore entity relationships and traverse the corporate graph
- **Universal Search**: Full-text search across companies, filings, and entities
- **Watchlists API**: Track companies and configure alerts

Architecture
------------
The backend follows a layered architecture:

1. **API Layer** (FastAPI routers) - HTTP request handling
2. **Schema Layer** (Pydantic models) - Request/response validation
3. **Model Layer** (SQLAlchemy ORM) - Database entities
4. **Database Layer** (PostgreSQL) - Persistent storage

Quick Start
-----------
.. code-block:: python

    # Run the development server
    uvicorn app.main:app --reload
    
    # Access API docs
    # Swagger UI: http://localhost:8000/docs
    # ReDoc: http://localhost:8000/redoc

Configuration
-------------
Environment variables (see .env.example):
- DATABASE_URL: PostgreSQL connection string
- SECRET_KEY: JWT signing key
- CORS_ORIGINS: Allowed origins for CORS

See Also
--------
- docs/API_OVERVIEW.md - Complete API documentation
- ../db/schema.sql - Database schema
- ../docs/FEATURE_ROADMAP.md - Feature roadmap
"""

__version__ = "0.1.0"
__author__ = "py-sec-edgar Team"
__all__ = ["app", "__version__"]
