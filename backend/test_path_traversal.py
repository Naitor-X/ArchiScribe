#!/usr/bin/env python3
"""
Test-Skript für Path Traversal Schutz.

Testet den /jobs/retrigger Endpunkt auf:
1. Path Traversal ../ wird blockiert
2. Absolute Pfade außerhalb von inbox werden blockiert
3. Ungültige Zeichen (Command Injection) werden abgelehnt
4. Nicht existierende Dateien geben 404
5. Gültige Pfade werden akzeptiert
"""

import asyncio
import shutil
import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
TEST_API_KEY = "sk-tenant-00000000-0000-0000-0000-000000000001-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def get_message(data: dict) -> str:
    """Extrahiert die Fehlermeldung aus der Response (detail oder message)."""
    return data.get("detail") or data.get("message") or ""


async def test_retrigger_path_traversal():
    """Test: Path Traversal ../../../etc/passwd sollte blockiert werden."""
    print("\n[TEST 1] Path Traversal '../../../etc/passwd'...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "../../../etc/passwd"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        msg = get_message(data).lower()
        assert "außerhalb" in msg or "ungültig" in msg, f"Unexpected message: {msg}"
        print(f"  ✓ Korrekt blockiert: {get_message(data)}")
        return True


async def test_retrigger_absolute_path():
    """Test: Absoluter Pfad /etc/passwd sollte blockiert werden."""
    print("\n[TEST 2] Absoluter Pfad '/etc/passwd'...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "/etc/passwd"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print(f"  ✓ Korrekt blockiert: {get_message(data)}")
        return True


async def test_retrigger_command_injection():
    """Test: Command Injection mit Semikolon sollte blockiert werden."""
    print("\n[TEST 3] Command Injection 'test;ls -la'...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "test;ls -la"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        msg = get_message(data)
        assert "nicht erlaubte Zeichen" in msg, f"Unexpected message: {msg}"
        print(f"  ✓ Korrekt blockiert: {msg}")
        return True


async def test_retrigger_pipe_injection():
    """Test: Pipe-Zeichen für Command Injection sollte blockiert werden."""
    print("\n[TEST 4] Pipe Injection 'test | cat /etc/passwd'...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "test | cat /etc/passwd"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        msg = get_message(data)
        assert "nicht erlaubte Zeichen" in msg, f"Unexpected message: {msg}"
        print(f"  ✓ Korrekt blockiert: {msg}")
        return True


async def test_retrigger_null_byte():
    """Test: Null-Byte Injection sollte blockiert werden."""
    print("\n[TEST 5] Null-Byte Injection...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "test.pdf\x00.jpg"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"  ✓ Korrekt blockiert: {get_message(data)}")
        return True


async def test_retrigger_nonexistent_file():
    """Test: Nicht existierende Datei sollte 404 geben."""
    print("\n[TEST 6] Nicht existierende Datei 'gibt-es-nicht.pdf'...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "gibt-es-nicht.pdf"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        msg = get_message(data).lower()
        assert "nicht gefunden" in msg, f"Unexpected message: {msg}"
        print(f"  ✓ Korrekt 404: {get_message(data)}")
        return True


async def test_retrigger_valid_path():
    """Test: Gültiger Pfad sollte Job erstellen oder Duplicate erkennen."""
    print("\n[TEST 7] Gültiger Pfad 'test_traversal.pdf'...")

    # Prüfe ob Test-PDF existiert
    test_pdf = Path("/files/Form2.pdf")
    if not test_pdf.exists():
        print("  ⚠ Test-PDF /files/Form2.pdf nicht gefunden, überspringe Test")
        return None

    # Kopiere Test-PDF in inbox
    inbox_path = Path("/files/inbox")
    inbox_path.mkdir(parents=True, exist_ok=True)
    test_copy = inbox_path / "test_traversal.pdf"

    if not test_copy.exists():
        shutil.copy(test_pdf, test_copy)
        print(f"  Kopiert: {test_pdf} → {test_copy}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "test_traversal.pdf"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        if response.status_code == 200:
            assert "job_id" in data, f"Expected job_id in response: {data}"
            print(f"  ✓ Job erfolgreich erstellt: {data['job_id']}")
            return True
        elif response.status_code == 409:
            print("  ✓ Datei bereits verarbeitet (Duplicate erkannt)")
            return True
        elif response.status_code == 400 and "bereits" in get_message(data).lower():
            print("  ✓ Datei bereits in Verarbeitung")
            return True
        else:
            print(f"  ✗ Unerwarteter Status: {response.status_code}")
            return False


async def test_retrigger_nested_path():
    """Test: Gültiger verschachtelter Pfad (falls Unterordner existiert)."""
    print("\n[TEST 8] Verschachtelter Pfad 'subdir/nested.pdf' (negativ - existiert nicht)...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BASE_URL}/jobs/retrigger",
            headers={"X-API-Key": TEST_API_KEY},
            json={"file_path": "subdir/nested.pdf"},
        )

        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {data}")

        # Sollte 404 geben (Datei existiert nicht)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"  ✓ Korrekt 404 für nicht existierenden Unterordner")
        return True


async def run_all_tests():
    """Führt alle Tests aus."""
    print("=" * 60)
    print("Path Traversal Schutz - Integration Tests")
    print("=" * 60)

    tests = [
        ("Path Traversal ../", test_retrigger_path_traversal),
        ("Absoluter Pfad", test_retrigger_absolute_path),
        ("Command Injection ;", test_retrigger_command_injection),
        ("Command Injection |", test_retrigger_pipe_injection),
        ("Null-Byte Injection", test_retrigger_null_byte),
        ("Nicht existierende Datei", test_retrigger_nonexistent_file),
        ("Gültiger Pfad", test_retrigger_valid_path),
        ("Verschachtelter Pfad", test_retrigger_nested_path),
    ]

    results = []

    # Prüfe ob Server läuft
    print("\nPrüfe Server-Verbindung...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            health = await client.get(f"{BASE_URL}/health")
            if health.status_code != 200:
                print(f"  ✗ Server nicht bereit: {health.status_code}")
                print("\nStarte Server mit:")
                print("  cd backend && source venv/bin/activate && uvicorn app.main:app --reload")
                return False
            print(f"  ✓ Server bereit: {health.json()}")
    except Exception as e:
        print(f"  ✗ Server nicht erreichbar: {e}")
        print("\nStarte Server mit:")
        print("  cd backend && source venv/bin/activate && uvicorn app.main:app --reload")
        return False

    # Tests ausführen
    print("\n" + "=" * 60)
    print("TESTS")
    print("=" * 60)

    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success, None))
        except AssertionError as e:
            print(f"  ✗ Assertion Fehler: {e}")
            results.append((name, False, str(e)))
        except Exception as e:
            print(f"  ✗ Fehler: {e}")
            results.append((name, False, str(e)))

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ERGEBNISSE")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for name, success, error in results:
        if success is None:
            print(f"  ○ {name}: ÜBERSPRUNGEN")
            skipped += 1
        elif success:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}: {error}")
            failed += 1

    print(f"\nGesamt: {passed} bestanden, {failed} fehlgeschlagen, {skipped} übersprungen")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
