from sqlalchemy import Boolean, Column, Integer, String, Enum
from .base import BaseModel
from passlib.context import CryptContext
from sqlalchemy.orm import relationship

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """管理员角色常量。

    注意：本模块顶部的 Enum 来自 sqlalchemy（不是标准库 enum.Enum），
    因此 UserRole 并非真正的枚举类 —— UserRole.ADMIN 只是普通的字符串 "admin"，
    没有 .value / .name 属性。比较时直接用 UserRole.ADMIN 或字面量 "admin"。
    """

    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class Admin(BaseModel):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role = Column(String(20), default=UserRole.ADMIN, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.password)
