"""
Middleware-Module für ArchiScribe API.

Enthält:
- Auth-Middleware für API-Key-Validierung
- Tenant-Middleware für Mandanten-Extraktion
- Error-Handler für einheitliche Fehler-Responses
"""

from app.middleware.auth import APIKeyMiddleware, get_current_tenant
from app.middleware.error_handler import (
    APIError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    api_error_handler,
)
from app.middleware.tenant import TenantContext

__all__ = [
    "APIKeyMiddleware",
    "get_current_tenant",
    "TenantContext",
    "APIError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "api_error_handler",
]
