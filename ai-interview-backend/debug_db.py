import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    # 使用你 .env 中的配置
    DATABASE_URL = "postgresql+asyncpg://postgres:123456@localhost:5432/postgres"
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL)
    try:
        async with engine.connect() as conn:
            # 1. 检查所有表
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables found in public schema: {tables}")
            
            # 2. 检查 alembic_version
            ver_res = await conn.execute(text("SELECT version_num FROM alembic_version"))
            version = ver_res.scalar()
            print(f"Current Alembic Version in DB: {version}")
            
            if 'resumes' in tables:
                print("SUCCESS: 'resumes' table exists!")
            else:
                print("ERROR: 'resumes' table NOT found!")
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_db())
