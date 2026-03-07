"""
Request-Logging Middleware.

Protokolliert alle API-Requests für Debugging und Monitoring.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware für Request-Logging.

    Loggt:
    - HTTP-Methode und Pfad
    - Response-Status-Code
    - Verarbeitungszeit
    - Tenant-ID (falls vorhanden)
    """

    # Pfade, die nicht geloggt werden sollen
    SKIP_PATHS = {
        "/health",
        "/favicon.ico",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Pfad prüfen
        path = request.url.path

        # Health-Check nicht loggen
        if path in self.SKIP_PATHS:
            return await call_next(request)

        # Start-Zeit
        start_time = time.time()

        # Request-Details
        method = request.method
        query = str(request.query_params) if request.query_params else ""

        # Response ausführen
        response = await call_next(request)

        # Verarbeitungszeit berechnen
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)

        # Tenant-Info (falls vorhanden)
        tenant_id = "-"
        if hasattr(request.state, "tenant_id"):
            tenant_id = str(request.state.tenant_id)[:8]

        # Log-Level basierend auf Status-Code
        status_code = response.status_code
        log_level = logging.INFO

        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING

        # Log-Eintrag
        log_message = f"{method} {path}"
        if query:
            log_message += f"?{query}"
        log_message += f" -> {status_code} ({process_time_ms}ms) [tenant={tenant_id}]"

        logger.log(log_level, log_message)

        # Response-Time Header hinzufügen
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)

        return response
