# ArchiScribe

KI-gestützte Verarbeitung von Grundlagenformularen für Architekturbüros.

## Schnellstart

### Backend starten

```bash
# Ins Backend-Verzeichnis wechseln
cd backend

# Virtuelle Umgebung aktivieren
source venv/bin/activate

# Anwendung starten (mit Hot-Reload)
uvicorn app.main:app --reload

# Oder mit anderem Port (falls 8000 belegt)
uvicorn app.main:app --reload --port 8001
```

### Frontend starten

```bash
# Ins Frontend-Verzeichnis wechseln
cd frontend/archiscribe

# Dependencies installieren (nur beim ersten Mal)
npm install

# Entwicklungsserver starten
npm run dev
```

## Ports

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Dokumentation**: http://localhost:8000/docs (Swagger UI)

## Häufige Probleme

### Port bereits belegt

```bash
# Prozess finden, der Port 8000 nutzt
lsof -i :8000

# Prozess beenden
kill -9 <PID>
```

### ModuleNotFoundError

Falls `ModuleNotFoundError: No module named 'app'` auftritt:
- Nicht `python3 app/main.py` verwenden
- Stattdessen `uvicorn app.main:app --reload` nutzen

## Weitere Dokumentation

- [Datenbank-Dokumentation](docs/DATABASE.md)
- [Projekt-Anleitung](CLAUDE.md)
