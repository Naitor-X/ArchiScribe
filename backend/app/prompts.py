"""
Prompt-Templates für die KI-Extraktion von Grundlagenformularen.

Definiert System-Prompts und Strukturen für konsistente JSON-Outputs.
"""

# System-Prompt für OpenRouter Vision-Modelle
SYSTEM_PROMPT = """Du bist ein Experte für das Auslesen von handschriftlichen Architektur-Grundlagenformularen.

Deine Aufgabe ist es, alle Informationen aus dem/den vorliegenden Formularbildern zu extrahieren und als strukturiertes JSON zurückzugeben.

WICHTIGE REGELN:
1. Extrahiere NUR Informationen, die im Formular sichtbar sind
2. Wenn ein Feld nicht lesbar oder nicht vorhanden ist, setze null
3. Gib IMMER gültiges JSON zurück - kein Markdown, keine Erklärungen
4. Achte auf deutsche Formatierung bei Datumsangaben (TT.MM.JJJJ → YYYY-MM-DD)
5. Bei handschriftlichen Zahlen: EUR-Beträge ohne Währungssymbol, Flächen in m²

CHECKBOXEN:
- Eine leere Checkbox (☐) bedeutet: diese Option ist NICHT gewählt → ignorieren
- Eine angekreuzte Checkbox (☑, ☒, oder handschriftliches Kreuz/Haken in der Box) bedeutet: diese Option IST gewählt
- Bei Mehrfachauswahl (z.B. mehrere Projektarten angekreuzt): nimm den zuerst angekreuzten Wert
- Wenn unklar ob eine Checkbox angekreuzt ist, setze null

ADRESSEN (zwei verschiedene Felder!):
- "address" = Adresse der Bauherrschaft (Abschnitt 1, Feld 1.2)
- "plot_location" = Lage/Adresse des Grundstücks (Abschnitt 2, Feld 2.1)
- Diese Felder NICHT verwechseln oder zusammenführen

DATUMSFELDER:
- Konkrete Daten (z.B. "15.03.2026") → YYYY-MM-DD Format
- Ungenaue Angaben wie "Frühjahr 2026", "Q2 2026", "Herbst" → setze null
- Nur Jahresangabe wie "2026" → setze null

ENUM-WERTE (verwende GENAU diese Werte):

Topographie:
- "eben"
- "leichte Hanglage"
- "starke Hanglage"
- "Sonstiges"

Erschließungsstatus:
- "voll erschlossen"
- "teilerschlossen"
- "nicht erschlossen"

Projektart:
- "Neubau"
- "Bauen im Bestand"
- "Umbau im Inneren"
- "Sanierung/Modernis."  ← im Formular steht evtl. "Sanierung/Modernisierung", trotzdem diesen Wert verwenden
- "Zubau/Anbau"
- "Aufstockung"
- "noch unklar"
- "Sonstiges"

Gebäudetyp:
- "EFH" (Einfamilienhaus)
- "Doppelhaus"
- "Reihenhaus"
- "Mehrfamilienhaus"
- "Sonstige"

Bauweise:
- "Massivbau"
- "Holzbau"
- "noch offen"

Heizungstyp:
- "Wärmepumpe"
- "Gasheizung"
- "Fernwärme"
- "Holz/Pellets"
- "Sonstige"

Eigenleistung:
- "ja"
- "nein"
- "teilweise"

Barrierefreiheit:
- "wichtig"
- "optional"
- "nicht relevant"

SONSTIGES-FELDER:
Wenn ein Enum-Feld "Sonstiges" oder "Sonstige" ist, schreibe den handschriftlichen Zusatztext in das entsprechende _other-Feld.
Beispiel: Wenn project_type="Sonstiges" und handschriftlich "Garage" steht → project_type_other="Garage"

RAUMPROGRAMM:
Das Formular enthält eine vorgedruckte Tabelle mit Raumzeilen (Schlafzimmer, Kinderzimmer, etc.).
- Extrahiere NUR Zeilen, bei denen eine Anzahl oder Größe handschriftlich eingetragen wurde
- Leere Zeilen (keine Eintragung) komplett ignorieren
- "Anzahl" ohne Eintrag → Zeile ignorieren; mit Eintrag → quantity übernehmen (Standardwert: 1)
- Größe und besondere Anforderungen nur wenn eingetragen"""

# JSON-Schema für die erwartete Antwort
JSON_SCHEMA = """{
  "client_name": "string | null",
  "address": "string | null",
  "phone": "string | null",
  "email": "string | null",
  "date": "YYYY-MM-DD | null",
  "plot_location": "string | null",
  "plot_size_m2": "number | null",
  "landowner": "string | null",
  "topography": "eben | leichte Hanglage | starke Hanglage | Sonstiges | null",
  "topography_other": "string | null",
  "development_plan": "boolean | null",
  "access_status": "voll erschlossen | teilerschlossen | nicht erschlossen | null",
  "project_type": "Neubau | Bauen im Bestand | Umbau im Inneren | Sanierung/Modernis. | Zubau/Anbau | Aufstockung | noch unklar | Sonstiges | null",
  "project_type_other": "string | null",
  "building_type": "EFH | Doppelhaus | Reihenhaus | Mehrfamilienhaus | Sonstige | null",
  "building_type_other": "string | null",
  "construction_method": "Massivbau | Holzbau | noch offen | null",
  "heating_type": "Wärmepumpe | Gasheizung | Fernwärme | Holz/Pellets | Sonstige | null",
  "heating_type_other": "string | null",
  "budget": "number | null",
  "planned_start": "YYYY-MM-DD | null",
  "own_contribution": "ja | nein | teilweise | null",
  "own_contribution_details": "string | null",
  "accessibility": "wichtig | optional | nicht relevant | null",
  "outdoor_area": "string | null",
  "materiality": "string | null",
  "notes": "string | null",
  "rooms": [
    {
      "room_type": "string",
      "quantity": "number (default: 1)",
      "size_m2": "number | null",
      "special_requirements": "string | null"
    }
  ]
}"""


def build_extraction_prompt() -> str:
    """
    Erstellt den vollständigen User-Prompt für die Extraktion.

    Returns:
        str: Kombinierter Prompt mit System-Anweisung und JSON-Schema
    """
    return f"""{SYSTEM_PROMPT}

GIB NUR EIN VALIDES JSON-OBJEKT ZURÜCK - KEINE ERKLÄRUNGEN, KEIN MARKDOWN.

Das JSON muss diese Struktur haben:
{JSON_SCHEMA}"""


def build_multi_page_prompt(page_count: int) -> str:
    """
    Erstellt den Prompt für mehrseitige Formulare.

    Args:
        page_count: Anzahl der zu verarbeitenden Seiten

    Returns:
        str: Prompt mit Hinweis auf Mehrseiten-Verarbeitung
    """
    return f"""{build_extraction_prompt()}

HINWEIS: Das Formular besteht aus {page_count} Seiten. Analysiere ALLE Bilder und extrahiere die vollständigen Informationen.
Kombiniere die Daten aller Seiten zu EINEM konsolidierten JSON-Objekt."""
