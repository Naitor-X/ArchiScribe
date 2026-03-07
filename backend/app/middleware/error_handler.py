"""
Unified Error Handler für API-Responses.

Stellt einheitliche Fehlerformate für alle API-Endpunkte bereit.
"""

import logging
import traceback
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Basis-Exception für API-Fehler.

    Liefert ein einheitliches Response-Format.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "error",
        details: Any = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(message)

    def to_response(self) -> dict:
        """Konvertiert zu JSON-Response-Format."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class AuthenticationError(APIError):
    """Fehler bei der Authentifizierung."""

    def __init__(self, message: str = "Authentifizierung fehlgeschlagen", details: Any = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="unauthorized",
            details=details,
        )


class ForbiddenError(APIError):
    """Keine Berechtigung für diese Ressource."""

    def __init__(self, message: str = "Keine Berechtigung", details: Any = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="forbidden",
            details=details,
        )


class NotFoundError(APIError):
    """Ressource nicht gefunden."""

    def __init__(self, resource: str, resource_id: str | None = None):
        details = {resource: resource_id} if resource_id else None
        super().__init__(
            message=f"{resource} nicht gefunden",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="not_found",
            details=details,
        )


class ValidationError(APIError):
    """Validierungsfehler."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="validation_error",
            details=details,
        )


class ConflictError(APIError):
    """Konflikt (z.B. Duplikat)."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="conflict",
            details=details,
        )


class RateLimitError(APIError):
    """Rate Limit überschritten."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate Limit überschritten",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="rate_limit_exceeded",
            details={"retry_after_seconds": retry_after},
        )
        self.retry_after = retry_after


class InternalError(APIError):
    """Interner Server-Fehler."""

    def __init__(self, message: str = "Interner Server-Fehler", details: Any = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="internal_error",
            details=details,
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handler für APIError-Exceptions.

    Wird in FastAPI registriert für einheitliche Fehler-Responses.
    """
    # Loggen (nur Server-Fehler als Error)
    if exc.status_code >= 500:
        logger.error(f"API Error: {exc.error_code} - {exc.message}")
    else:
        logger.warning(f"API Error: {exc.error_code} - {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler für FastAPI HTTPException.

    Konvertiert zu einheitlichem Format.
    """
    # Standard-Fehler-Format
    error_code = "error"
    message = str(exc.detail)
    details = None

    # Spezifische Fehler-Codes basierend auf Status
    if exc.status_code == 401:
        error_code = "unauthorized"
    elif exc.status_code == 403:
        error_code = "forbidden"
    elif exc.status_code == 404:
        error_code = "not_found"
    elif exc.status_code == 422:
        error_code = "validation_error"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": message,
            "details": details,
        },
    )


async def pydantic_validation_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """
    Handler für Pydantic ValidationErrors.

    Wandelt Validierungsfehler in lesbare Meldungen um.
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(f"Validierungsfehler: {len(errors)} Fehler")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Validierungsfehler",
            "details": {"errors": errors},
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler für alle anderen Exceptions.

    Verhindert, dass interne Details nach außen dringen.
    """
    # Stack-Trace loggen
    logger.error(f"Unerwarteter Fehler: {exc}\n{traceback.format_exc()}")

    # In Production keine Details preisgeben
    if True:  # Immer generische Meldung
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "Ein unerwarteter Fehler ist aufgetreten",
                "details": None,
            },
        )
