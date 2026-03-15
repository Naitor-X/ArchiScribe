"""API-Router für Tenant-Endpunkte."""

from fastapi import APIRouter

from app.database import list_tenants
from app.schemas.project import TenantResponse

router = APIRouter(prefix="/tenants", tags=["Mandanten"])


@router.get("", response_model=list[TenantResponse])
async def list_tenants_endpoint() -> list[TenantResponse]:
    """
    Listet alle Mandanten (Architekturbüros).

    Nur für Admin-Zwecke gedacht.
    """
    tenants = await list_tenants()

    return [
        TenantResponse(
            id=t["id"],
            name=t["name"],
            created_at=t["created_at"],
        )
        for t in tenants
    ]
