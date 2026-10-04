"""
创建初始管理员账号
此脚本用于创建后台管理系统的第一个超级管理员账号。
"""
import os
import sys
import asyncio
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.base import get_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.admin import Admin


async def create_first_admin():
    """创建第一个超级管理员账号"""

    # 管理员信息：凭据一律从环境变量读取。
    # 历史上这里硬编码了管理员邮箱与明文口令并被提交进仓库 —— 等于把后台
    # 超级管理员账号直接公开（且该口令与服务器 root 口令相同），已移除。
    email = os.environ.get("INITIAL_ADMIN_EMAIL")
    password = os.environ.get("INITIAL_ADMIN_PASSWORD")
    first_name = os.environ.get("INITIAL_ADMIN_FIRST_NAME", "Admin")
    last_name = os.environ.get("INITIAL_ADMIN_LAST_NAME", "User")

    if not email or not password:
        raise SystemExit(
            "缺少环境变量 INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD。"
            "请显式设置后再运行，不要把口令写回代码。"
        )

    engine = get_engine()
    async with AsyncSession(engine) as session:
        # 检查管理员是否已存在
        result = await session.execute(
            select(Admin).where(Admin.email == email)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print(f"❌ 邮箱为 {email} 的管理员已存在！")
            return

        # 创建新的超级管理员
        hashed_password = Admin.get_password_hash(password)
        admin = Admin(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=hashed_password,
            role="superadmin",
            is_active=True
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print("✅ 超级管理员账号创建成功！")
        print(f"   邮箱: {email}")
        print(f"   姓名: {first_name} {last_name}")
        print(f"   角色: superadmin")
        print(f"   ID: {admin.id}")


if __name__ == "__main__":
    asyncio.run(create_first_admin())
