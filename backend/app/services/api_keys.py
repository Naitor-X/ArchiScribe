"""
API-Key Service.

Stellt Funktionen für API-Key-Generierung, -Verwaltung und -Validierung bereit.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.database import get_connection

logger = logging.getLogger(__name__)


def generate_api_key(tenant_id: UUID | str) -> tuple[str, str, str]:
    """
    Generiert einen neuen API-Key für einen Tenant.

    Format: sk-tenant-{tenant_id}-{random_32_chars}

    Args:
        tenant_id: UUID des Tenants

    Returns:
        Tuple (full_key, key_hash, key_prefix)
        - full_key: Der vollständige API-Key (nur einmalig sichtbar!)
        - key_hash: SHA-256 Hash für DB-Speicherung
        - key_prefix: Erste 20 Zeichen für Identifikation
    """
    if isinstance(tenant_id, UUID):
        tenant_id_str = str(tenant_id)
    else:
        tenant_id_str = tenant_id

    # 32 Zeichen Random-String
    random_part = secrets.token_hex(16)  # 16 Bytes = 32 Hex-Chars

    # API-Key zusammenbauen
    full_key = f"sk-tenant-{tenant_id_str}-{random_part}"

    # Hash für DB-Speicherung
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    # Prefix für schnelle Suche
    key_prefix = full_key[:20]

    return full_key, key_hash, key_prefix


async def create_api_key(
    tenant_id: UUID | str,
    name: str | None = None,
    expires_at: datetime | None = None,
) -> dict[str, Any]:
    """
    Erstellt einen neuen API-Key in der Datenbank.

    WICHTIG: Der vollständige Key wird nur einmalig zurückgegeben!

    Args:
        tenant_id: UUID des Tenants
        name: Optionaler Name (z.B. "Produktion", "Test")
        expires_at: Optionales Ablaufdatum

    Returns:
        Dict mit:
        - id: UUID des Eintrags
        - key: Der API-Key (nur hier sichtbar!)
        - key_prefix: Für Identifikation
        - name: Name des Keys
        - created_at: Erstellungsdatum
        - expires_at: Ablaufdatum
    """
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    # Key generieren
    full_key, key_hash, key_prefix = generate_api_key(tenant_id)

    async with get_connection() as conn:
        # Prüfen ob Prefix bereits existiert (sollte extrem unwahrscheinlich sein)
        existing = await conn.fetchval(
            "SELECT 1 FROM api_keys WHERE key_prefix = $1",
            key_prefix,
        )
        if existing:
            # Nochmal versuchen mit neuem Random
            full_key, key_hash, key_prefix = generate_api_key(tenant_id)

        # In DB einfügen
        row = await conn.fetchrow(
            """
            INSERT INTO api_keys (tenant_id, key_hash, key_prefix, name, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, created_at
            """,
            tenant_id,
            key_hash,
            key_prefix,
            name,
            expires_at,
        )

    logger.info(f"API-Key erstellt: {key_prefix}... für Tenant {tenant_id}")

    return {
        "id": str(row["id"]),
        "key": full_key,  # Wird nur einmalig zurückgegeben!
        "key_prefix": key_prefix,
        "name": name,
        "created_at": row["created_at"].isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


async def get_api_keys_for_tenant(
    tenant_id: UUID | str,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    """
    Listet alle API-Keys für einen Tenant.

    HINWEIS: Die eigentlichen Keys werden NICHT zurückgegeben!

    Args:
        tenant_id: UUID des Tenants
        include_inactive: Auch deaktivierte Keys auflisten

    Returns:
        Liste von Dicts mit Key-Informationen
    """
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        query = """
            SELECT
                id, key_prefix, name, is_active,
                last_used_at, created_at, expires_at
            FROM api_keys
            WHERE tenant_id = $1
        """
        if not include_inactive:
            query += " AND is_active = true"

        query += " ORDER BY created_at DESC"

        rows = await conn.fetch(query, tenant_id)

    return [
        {
            "id": str(row["id"]),
            "key_prefix": row["key_prefix"],
            "name": row["name"],
            "is_active": row["is_active"],
            "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
            "created_at": row["created_at"].isoformat(),
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
        }
        for row in rows
    ]


async def revoke_api_key(
    key_id: UUID | str,
    tenant_id: UUID | str,
) -> bool:
    """
    Widerruft (deaktiviert) einen API-Key.

    Args:
        key_id: UUID des API-Keys
        tenant_id: UUID des Tenants (für Sicherheitsprüfung)

    Returns:
        True wenn erfolgreich, False wenn Key nicht gefunden
    """
    if isinstance(key_id, str):
        key_id = UUID(key_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        result = await conn.execute(
            """
            UPDATE api_keys
            SET is_active = false
            WHERE id = $1 AND tenant_id = $2
            """,
            key_id,
            tenant_id,
        )

        success = result == "UPDATE 1"

        if success:
            logger.info(f"API-Key {key_id} widerrufen")

        return success


async def delete_api_key(
    key_id: UUID | str,
    tenant_id: UUID | str,
) -> bool:
    """
    Löscht einen API-Key permanent.

    HINWEIS: Normalerweise revoke_api_key() bevorzugen für Audit-Trail!

    Args:
        key_id: UUID des API-Keys
        tenant_id: UUID des Tenants (für Sicherheitsprüfung)

    Returns:
        True wenn erfolgreich, False wenn Key nicht gefunden
    """
    if isinstance(key_id, str):
        key_id = UUID(key_id)
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    async with get_connection() as conn:
        result = await conn.execute(
            """
            DELETE FROM api_keys
            WHERE id = $1 AND tenant_id = $2
            """,
            key_id,
            tenant_id,
        )

        success = result == "DELETE 1"

        if success:
            logger.info(f"API-Key {key_id} gelöscht")

        return success


async def ensure_test_api_key() -> str:
    """
    Stellt sicher, dass ein Test-API-Key für den Test-Tenant existiert.

    Wird für Entwicklung und Tests verwendet.

    Returns:
        Der Test-API-Key
    """
    from app.config import settings

    tenant_id = UUID(settings.test_tenant_id)

    async with get_connection() as conn:
        # Prüfen ob bereits ein Key existiert
        existing_key = await conn.fetchrow(
            """
            SELECT key_prefix FROM api_keys
            WHERE tenant_id = $1 AND name = 'Test-Key'
            """,
            tenant_id,
        )

        if existing_key:
            # Bestehender Key - wir können den echten Key nicht rekonstruieren
            # In Development-Modus verwenden wir den dev_api_key aus Config
            logger.info(f"Test-API-Key bereits vorhanden: {existing_key['key_prefix']}...")
            return settings.dev_api_key

        # Neuen Key erstellen
        result = await create_api_key(
            tenant_id=tenant_id,
            name="Test-Key",
        )

        logger.info(f"Test-API-Key erstellt: {result['key_prefix']}...")

        return result["key"]
