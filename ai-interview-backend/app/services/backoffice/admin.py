from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.models.admin import Admin, UserRole
from app.schemas.backoffice.admin import AdminCreate, AdminResponse
from app.exceptions.http_exceptions import APIException
from typing import List, Optional
from fastapi import status
from app.core.security import AuthBase


class AdminService:
    @staticmethod
    async def create_admin(db: AsyncSession, admin_data: AdminCreate) -> AdminResponse:
        """创建新管理员"""
        # 检查邮箱是否已存在
        email_query = select(Admin).where(Admin.email == admin_data.email)
        result = await db.execute(email_query)
        if result.scalar_one_or_none():
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email already exists"
            )
        
        # 创建新管理员
        hashed_password = AuthBase.hash_token(admin_data.password)
        admin = Admin(
            email=admin_data.email,
            first_name=admin_data.first_name,
            last_name=admin_data.last_name,
            password=hashed_password,
            is_active=admin_data.is_active,
            # 角色由入参决定（此前硬编码 superadmin，导致永远创建不出低权限管理员）
            role=admin_data.role,
        )
        
        db.add(admin)
        await db.flush()
        await db.refresh(admin)
        
        return AdminResponse.model_validate(admin)
    
    @staticmethod
    async def get_admin(db: AsyncSession, admin_id: int) -> Optional[AdminResponse]:
        """获取管理员详情"""
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()
        
        if not admin:
            return None
        
        return AdminResponse.model_validate(admin)
    
    @staticmethod
    async def get_admin_by_email(db: AsyncSession, email: str) -> Optional[Admin]:
        """通过邮箱获取管理员"""
        admin_query = select(Admin).where(Admin.email == email)
        result = await db.execute(admin_query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_admins(db: AsyncSession, offset: int = 0, limit: int = 100, email: str = None, sort_by: str = None, sort_order: str = "desc") -> List[AdminResponse]:
        """获取所有管理员列表"""
        admin_query = AdminService.get_admins_query(db, email, sort_by, sort_order).offset(offset).limit(limit)
        result = await db.execute(admin_query)
        admins = result.scalars().all()
        
        return [AdminResponse.model_validate(admin) for admin in admins]
    
    @staticmethod
    async def get_admins_query(db: AsyncSession, email: str = None, sort_by: str = None, sort_order: str = "desc"):
        """获取管理员查询对象，用于分页
        
        Args:
            db: 数据库会话
            email: 可选的邮箱过滤条件
            sort_by: 排序字段，默认为 created_at
            sort_order: 排序方向，asc 或 desc
        """
        query = select(Admin)
        
        # 添加过滤条件
        if email:
            query = query.where(Admin.email.ilike(f"%{email}%"))
        
        # 添加排序
        if sort_by == "email":
            if sort_order.lower() == "asc":
                query = query.order_by(Admin.email.asc())
            else:
                query = query.order_by(Admin.email.desc())
        else:  # 默认按创建时间排序
            if sort_order.lower() == "asc":
                query = query.order_by(Admin.created_at.asc())
            else:
                query = query.order_by(Admin.created_at.desc())
        
        return query
    
    @staticmethod
    async def update_admin(db: AsyncSession, admin_id: int, admin_data: dict) -> Optional[AdminResponse]:
        """更新管理员信息"""
        # 先检查管理员是否存在
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()
        
        if not admin:
            return None
        
        update_data = {}
        
        # 检查邮箱是否需要更新且是否已存在
        if "email" in admin_data and admin_data["email"] != admin.email:
            email_query = select(Admin).where(
                Admin.email == admin_data["email"],
                Admin.id != admin_id
            )
            result = await db.execute(email_query)
            if result.scalar_one_or_none():
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Email already exists"
                )
            update_data["email"] = admin_data["email"]
        
        # 如果有密码更新，需要哈希处理
        if "password" in admin_data:
            update_data["password"] = AuthBase.hash_token(admin_data["password"])

        # 更新名字
        if "first_name" in admin_data:
            update_data["first_name"] = admin_data["first_name"]
        
        # 更新名字
        if "last_name" in admin_data:
            update_data["last_name"] = admin_data["last_name"]
        
        # 更新活跃状态
        if "is_active" in admin_data:
            update_data["is_active"] = admin_data["is_active"]

        # 角色变更。降级最后一个超管会让后台彻底失去管理入口（没人能再创建/删除
        # 管理员），只能直连数据库才能恢复 —— 因此拦住。
        if admin_data.get("role"):
            new_role = admin_data["role"]
            if admin.role == UserRole.SUPERADMIN and new_role != UserRole.SUPERADMIN:
                await AdminService._assert_not_last_superadmin(db, action="降级")
            update_data["role"] = new_role

        # 执行更新
        if update_data:
            stmt = update(Admin).where(Admin.id == admin_id).values(**update_data)
            await db.execute(stmt)
            
            # 重新获取更新后的管理员信息
            admin_query = select(Admin).where(Admin.id == admin_id)
            result = await db.execute(admin_query)
            admin = result.scalar_one_or_none()
        
        return AdminResponse.model_validate(admin)
    
    @staticmethod
    async def delete_admin(db: AsyncSession, admin_id: int) -> bool:
        """删除管理员"""
        # 先检查管理员是否存在
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()
        
        if not admin:
            return False

        # 同 update_admin：不允许删掉最后一个超管，否则后台无人能再管理管理员
        if admin.role == UserRole.SUPERADMIN:
            await AdminService._assert_not_last_superadmin(db, action="删除")

        # 先删除关联的 admin_tokens
        from app.models.token import AdminToken
        delete_tokens_stmt = delete(AdminToken).where(AdminToken.admin_id == admin_id)
        await db.execute(delete_tokens_stmt)
        
        # 执行删除管理员
        stmt = delete(Admin).where(Admin.id == admin_id)
        await db.execute(stmt)
        
        return True
    
    @staticmethod
    async def change_password(db: AsyncSession, admin_id: int, current_password: str, new_password: str) -> bool:
        """修改管理员密码"""
        # 先检查管理员是否存在
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()
        
        if not admin:
            return False
        
        # 验证当前密码
        if not AuthBase.verify_token_hash(current_password, admin.password):
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Current password is incorrect"
            )
        
        # 更新密码
        hashed_password = AuthBase.hash_token(new_password)
        stmt = update(Admin).where(Admin.id == admin_id).values(password=hashed_password)
        await db.execute(stmt)
        
        return True
    
    @staticmethod
    async def reset_password(db: AsyncSession, admin_id: int, new_password: str) -> bool:
        """重置管理员密码（仅管理员本人和超管可操作）"""
        # 先检查管理员是否存在
        admin_query = select(Admin).where(Admin.id == admin_id)
        result = await db.execute(admin_query)
        admin = result.scalar_one_or_none()
        
        if not admin:
            return False
        
        # 更新密码
        hashed_password = AuthBase.hash_token(new_password)
        stmt = update(Admin).where(Admin.id == admin_id).values(password=hashed_password)
        await db.execute(stmt)
        
        return True

    @staticmethod
    async def _count_superadmins(db: AsyncSession) -> int:
        """当前超管数量，用于「不能失去最后一个超管」的保护。"""
        result = await db.execute(
            select(func.count())
            .select_from(Admin)
            .where(Admin.role == UserRole.SUPERADMIN)
        )
        return int(result.scalar() or 0)

    @staticmethod
    async def _assert_not_last_superadmin(db: AsyncSession, action: str) -> None:
        """最后一个超管不允许被降级或删除 —— 否则后台将无人能再管理管理员。"""
        if await AdminService._count_superadmins(db) <= 1:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"系统必须保留至少一个超级管理员，无法{action}最后一个超管"
            )


# 创建服务实例
admin_service = AdminService()