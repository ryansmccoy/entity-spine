"""
API Router - Version 1
"""
from fastapi import APIRouter

from app.api.v1.endpoints import companies, filings, entities, search, watchlists

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    companies.router,
    prefix="/companies",
    tags=["Companies"],
)
api_router.include_router(
    filings.router,
    prefix="/filings",
    tags=["Filings"],
)
api_router.include_router(
    entities.router,
    prefix="/entities",
    tags=["Entities & Knowledge Graph"],
)
api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
)
api_router.include_router(
    watchlists.router,
    prefix="/watchlists",
    tags=["Watchlists"],
)
