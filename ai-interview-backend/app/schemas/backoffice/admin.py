from ..base import BaseSchema, BaseResponseSchema, add_padded_id
from pydantic import EmailStr, Field
from typing import Literal, Optional


class AdminBase(BaseSchema):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None


class AdminCreate(AdminBase):
    password: str
    # 角色：admin = 普通管理员（只能改自己的密码/资料），superadmin = 超级管理员。
    # 此前 service 把 role 硬编码成 superadmin，导致永远创建不出低权限账号。
    # 默认值刻意保持 superadmin：管理端暂无角色选择 UI，若改默认会让「创建管理员」
    # 按钮的行为静默变化（新账号权限突然变小却毫无提示）。
    # 需要创建低权限账号时，在请求体里显式传 role="admin"。
    role: Literal["admin", "superadmin"] = "superadmin"


class AdminUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    # 此前该字段缺失，但路由 admin.py:111 会读取 admin_data.role —— 只要当前登录者
    # 不是超管就必然 AttributeError 500。该路径此前被「所有管理员都是超管」掩盖着。
    role: Optional[Literal["admin", "superadmin"]] = None


@add_padded_id()
class AdminResponse(BaseResponseSchema, AdminBase):
    is_active: bool
    role: str
    padded_id: Optional[str] = None

    @classmethod
    def model_validate(cls, admin):
        return super().model_validate(admin)


class AdminChangePassword(BaseSchema):
    current_password: str
    new_password: str = Field(..., min_length=8)

class ResetPassword(BaseSchema):
    password: str = Field(..., min_length=8)


class AdminFilter(BaseSchema):
    email: Optional[str] = None
    is_active: Optional[bool] = None
