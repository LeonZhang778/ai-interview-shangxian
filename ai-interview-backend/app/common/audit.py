from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    admin_id: int,
    action: str,
    target_type: str,
    target_id: int = None,
    detail: str = None,
    ip: str = None,
):
    db.add(AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip,
    ))
    await db.commit()
