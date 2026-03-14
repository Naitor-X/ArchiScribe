"""Router-Module für ArchiScribe API."""

from app.routers.projects import router as projects_router
from app.routers.tenants import router as tenants_router

__all__ = ["projects_router", "tenants_router"]
