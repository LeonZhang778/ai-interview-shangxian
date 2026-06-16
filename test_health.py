import asyncio
import sys

async def test():
    # Test DB
    try:
        from app.db.session import get_db
        from sqlalchemy import text
        async for db in get_db():
            r = await db.execute(text("SELECT 1"))
            print("DB OK:", r.scalar())
            break
    except Exception as e:
        print("DB ERROR:", e)

    # Test Redis
    try:
        from app.services.common.redis import redis_client
        result = await redis_client.get("test_key")
        print("REDIS OK, get result:", result)
    except Exception as e:
        print("REDIS ERROR:", e)

asyncio.run(test())
