from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.db.session import get_db
from app.core.security import AuthBase
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
'''
这行是 FastAPI + OAuth2 密码模式 的标准配置，核心作用：
OAuth2PasswordBearer：FastAPI 内置的 OAuth2 密码流依赖项，用于从请求头自动提取 Bearer Token。
tokenUrl：指定获取 Token 的接口地址，客户端要到这个地址（登录接口）提交账号密码换取 token。
settings.API_V1_STR：项目配置里的 API 版本前缀（如 /api/v1），拼接后完整登录地址类似 /api/v1/auth/login。
oauth2_scheme：生成一个依赖对象，后续接口通过 Depends(oauth2_scheme) 校验、获取 token。
简单说：定义了 “去哪里登录拿 token”，并提供自动解析请求头 token 的工具
'''

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    payload = AuthBase.verify_token(token, scope="client")
    if not payload:
        raise HTTPException(
            status_code=403,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    user_query = select(User).where(User.id == int(user_id))
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=403, detail="无效的认证凭据")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="用户已被禁用")
    return user


async def get_current_user_optional(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """获取当前用户（可选），未登录或 token 无效时返回 None"""
    try:
        payload = AuthBase.verify_token(token, scope="client")
        if not payload:
            return None
        user_id = payload.get("sub")
        user_query = select(User).where(User.id == int(user_id))
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None
        return user
    except HTTPException:
        return None
