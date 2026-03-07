#!/usr/bin/env python3
"""
Test-Skript für API-Key Authentifizierung.

Testet:
1. Health-Check ohne Auth
2. Authentifizierung mit API-Key
3. Ungültiger API-Key
4. Fehlender API-Key
"""

import asyncio
import sys

import httpx

BASE_URL = "http://localhost:8000"
TEST_API_KEY = "sk-tenant-00000000-0000-0000-0000-000000000001-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


async def test_health_check():
    """Test 1: Health-Check ohne Authentifizierung."""
    print("\n[TEST 1] Health-Check ohne Auth...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "ok", f"Expected 'ok', got {data['status']}"
        print(f"  ✓ Status: {response.status_code}")
        print(f"  ✓ Response: {data['status']}")
        return True


async def test_auth_with_valid_key():
    """Test 2: Authentifizierung mit gültigem API-Key."""
    print("\n[TEST 2] Auth mit gültigem API-Key...")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/auth/test",
            headers={"X-API-Key": TEST_API_KEY},
        )

        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["authenticated"] is True
        print("  ✓ Authentifizierung erfolgreich")
        return True


async def test_auth_with_bearer_token():
    """Test 3: Authentifizierung mit Bearer Token."""
    print("\n[TEST 3] Auth mit Bearer Token...")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/auth/test",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        )

        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["authenticated"] is True
        print("  ✓ Bearer Token Authentifizierung erfolgreich")
        return True


async def test_auth_with_invalid_key():
    """Test 4: Authentifizierung mit ungültigem API-Key."""
    print("\n[TEST 4] Auth mit ungültigem API-Key...")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/auth/test",
            headers={"X-API-Key": "sk-tenant-invalid-key"},
        )

        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        data = response.json()
        assert data["error"] == "unauthorized"
        print("  ✓ Korrekt abgelehnt mit 401")
        return True


async def test_auth_without_key():
    """Test 5: Authentifizierung ohne API-Key.

    HINWEIS: Im Development-Modus wird der dev_api_key als Fallback verwendet.
    In Production würde dieser Test 401 zurückgeben.
    """
    print("\n[TEST 5] Auth ohne API-Key (Development-Modus)...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/auth/test")

        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")

        # Im Development-Modus wird der dev_api_key verwendet
        # In Production wäre dies 401
        assert response.status_code == 200, f"Expected 200 (dev mode), got {response.status_code}"
        data = response.json()
        assert data["authenticated"] is True
        print("  ✓ Development-Modus: dev_api_key als Fallback verwendet")
        return True


async def test_tenant_info():
    """Test 6: Tenant-Info Endpunkt."""
    print("\n[TEST 6] Tenant-Info Endpunkt...")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/tenants/me",
            headers={"X-API-Key": TEST_API_KEY},
        )

        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "tenant_id" in data
        print(f"  ✓ Tenant-ID: {data['tenant_id']}")
        return True


async def test_error_format():
    """Test 7: Einheitliches Fehler-Format."""
    print("\n[TEST 7] Fehler-Format Test...")
    async with httpx.AsyncClient() as client:
        # Nicht existierender Job
        response = await client.get(
            f"{BASE_URL}/jobs/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": TEST_API_KEY},
        )

        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")

        assert response.status_code == 404
        data = response.json()
        # Prüfen ob Fehler-Format korrekt ist
        assert "error" in data or "detail" in data
        print("  ✓ Fehler-Format korrekt")
        return True


async def run_all_tests():
    """Führt alle Tests aus."""
    print("=" * 60)
    print("API-Key Authentifizierungs-Tests")
    print("=" * 60)

    tests = [
        ("Health-Check", test_health_check),
        ("Gültiger API-Key", test_auth_with_valid_key),
        ("Bearer Token", test_auth_with_bearer_token),
        ("Ungültiger API-Key", test_auth_with_invalid_key),
        ("Ohne API-Key", test_auth_without_key),
        ("Tenant-Info", test_tenant_info),
        ("Fehler-Format", test_error_format),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success, None))
        except Exception as e:
            print(f"  ✗ Fehler: {e}")
            results.append((name, False, str(e)))

    print("\n" + "=" * 60)
    print("Ergebnisse:")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, success, error in results:
        if success:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}: {error}")
            failed += 1

    print(f"\nGesamt: {passed} bestanden, {failed} fehlgeschlagen")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
