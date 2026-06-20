from sqlalchemy import Column, Integer, String, Text, ForeignKey
from .base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    action = Column(String(50), nullable=False)  # login / create / update / delete / disable / enable / approve / reject
    target_type = Column(String(50), nullable=False)  # user / experience / announcement / admin / setting / feedback
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
