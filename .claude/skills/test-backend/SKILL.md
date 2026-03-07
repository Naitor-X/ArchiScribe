---
name: test-backend
description: Führt einen vollständigen Backend-Test durch - setzt DB/Files zurück, kopiert Test-PDF und überwacht die Verarbeitung. Bei Fehlern wird iteriert bis es klappt.
user-invocable: true
---

# Backend-Integrationstest

Führe einen vollständigen Backend-Test durch. Die Umgebung kann komplett zurückgesetzt werden - es gibt keine produktiven Daten.

## Test-Ablauf

### Schritt 1: Umgebung zurücksetzen

Leere zuerst die Datenbank UND alle Dateiordner vollständig:

```bash
# Datenbank komplett leeren (ohne Bestätigungsabfrage)
cd /home/clemens/projekte/dynplex/ArchiScribe/backend && source venv/bin/activate && python3 tools/clean_db.py --force && python3 tools/clean_files.py
```

### Schritt 2: Test-PDF bereitstellen

Kopiere das Testformular in die Inbox:

```bash
cp /home/clemens/projekte/dynplex/ArchiScribe/files/meinformular.pdf /home/clemens/projekte/dynplex/ArchiScribe/backend/files/inbox/
```

### Schritt 3: Backend starten

Starte das Backend im Hintergrund mit uvicorn:

```bash
cd /home/clemens/projekte/dynplex/ArchiScribe/backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Führe dies im Hintergrund aus und warte kurz bis der Server bereit ist.

### Schritt 4: Verarbeitung überwachen

Überwache die Verarbeitung durch wiederholte API-Checks:

```bash
# Health-Check alle 5 Sekunden
curl -s http://localhost:8000/health

# Queue-Status prüfen
curl -s http://localhost:8000/queue/stats

# Aktive Jobs anzeigen
curl -s http://localhost:8000/jobs
```

Die KI-Extraktion dauert typischerweise 30-60 Sekunden.

### Schritt 5: Ergebnis validieren

**Bei Erfolg:**
- Prüfe ob Projekt in der Datenbank erstellt wurde
- Prüfe ob PDF ins `archive/` verschoben wurde
- Zeige extrahierte Daten an

**Bei Fehler:**
- Lies die Backend-Logs
- Prüfe ob PDF im `error/` Ordner liegt
- Analysiere den Fehler und behebe ihn
- **WICHTIG: Wiederhole ab Schritt 1** - iteriere bis es funktioniert!

### Schritt 6: Abschlussbericht

Melde am Ende:
- ✅ **Erfolg**: Projekt-ID, Anzahl extrahierte Felder, Anzahl Räume
- ❌ **Fehler**: Was wurde versucht, was ist fehlgeschlagen

## Wichtige Regeln

1. **Iteriere bis zum Erfolg** - gib nicht nach dem ersten Fehler auf
2. **Datenbank ist sicher** - kann jederzeit komplett geleert werden
3. **Logs analysieren** - Backend-Logs enthalten alle wichtigen Informationen
4. **Geduld haben** - Vision-Modelle brauchen Zeit für PDFs

## Pfade

- Backend: `/home/clemens/projekte/dynplex/ArchiScribe/backend`
- Test-PDF: `/home/clemens/projekte/dynplex/ArchiScribe/files/meinformular.pdf`
- Inbox: `/home/clemens/projekte/dynplex/ArchiScribe/backend/files/inbox/`
- Archive: `/home/clemens/projekte/dynplex/ArchiScribe/backend/files/archive/`
- Error: `/home/clemens/projekte/dynplex/ArchiScribe/backend/files/error/`
