from fastapi import Request
from fastapi.responses import JSONResponse


class ArchiScribeException(Exception):
    """Basis-Exception für alle ArchiScribe-Fehler."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class PDFVerarbeitungsFehler(ArchiScribeException):
    """Fehler bei der PDF-Verarbeitung."""

    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class KIExtraktionsFehler(ArchiScribeException):
    """Fehler bei der KI-Extraktion via OpenRouter."""

    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class DatenbankFehler(ArchiScribeException):
    """Fehler bei Datenbankoperationen."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class DateiNichtGefunden(ArchiScribeException):
    """Angeforderte Datei existiert nicht."""

    def __init__(self, dateiname: str):
        super().__init__(f"Datei nicht gefunden: {dateiname}", status_code=404)


class UngueltigesDateiformat(ArchiScribeException):
    """Dateiformat wird nicht unterstützt."""

    def __init__(self, dateiname: str):
        super().__init__(
            f"Ungültiges Dateiformat für: {dateiname}. Nur PDF-Dateien erlaubt.",
            status_code=400,
        )


async def archiscribe_exception_handler(
    request: Request, exc: ArchiScribeException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"fehler": exc.message, "status_code": exc.status_code},
    )
