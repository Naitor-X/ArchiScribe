"""
Tenant-Context-Management.

Stellt Utilities für Multi-Tenant-Isolierung bereit.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class TenantContext:
    """
    Kontext-Objekt für den aktuellen Tenant.

    Enthält alle relevanten Informationen für Multi-Tenant-Queries.
    """

    tenant_id: UUID
    key_id: UUID | None = None
    key_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TenantContext":
        """Erstellt TenantContext aus Dict."""
        return cls(
            tenant_id=data["tenant_id"],
            key_id=data.get("key_id"),
            key_name=data.get("key_name"),
        )

    def __str__(self) -> str:
        return f"Tenant({self.tenant_id})"


def get_tenant_filter_column() -> str:
    """
    Gibt die Spalte zurück, die für Tenant-Filterung verwendet wird.

    Returns:
        Spaltenname (normalerweise 'tenant_id')
    """
    return "tenant_id"
