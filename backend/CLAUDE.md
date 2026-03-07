# Backend CLAUDE.md

## Implementierungsfortschritt

### Hauptmodul 1: PDF-Verarbeitung & KI-Extraktion

#### 1.1 Backend-Infrastruktur ✅ (2026-03-07)
- FastAPI-Grundstruktur mit Health-Check
- Pydantic-Settings für Konfiguration
- Logging-System mit konfigurierbarem Level
- Error-Handling mit custom Exceptions

#### 1.2 Datei-Management ✅ (2026-03-07)
- Ordnerstruktur: `inbox/`, `processing/`, `archive/`, `error/`
- Watchdog-Service für PDF-Überwachung
- PDF-Validierung (Magic-Bytes, Größe)
- Datei-Handling mit Hash-basierter Duplicate-Erkennung
- Modul: `app/file_utils.py`, `app/file_watcher.py`

#### 1.3 PDF-Konvertierung ✅ (2026-03-07)
- PDF-zu-Bild mit `pdf2image` + `poppler-utils`
- Bild-Optimierung mit `Pillow` (DPI 200, Max 2000x3000px)
- Base64-Encoding für API-Übertragung
- Multi-Page-Handling
- Modul: `app/pdf_converter.py`

## Test-PDF

**Original:** `/files/inbox/Form2.pdf` (4 Seiten, ~1MB)
- **WICHTIG:** Immer kopieren, nie verschieben!

## Lesson Learned

_Noch keine Einträge_
