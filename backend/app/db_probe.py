import asyncio
from sqlalchemy import text
from app.db.base import engine

async def probe():
    async with engine.connect() as conn:
        # Check tables
        tables_res = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        ))
        tables = [row[0] for row in tables_res.fetchall()]
        print(f"Tables in DB: {tables}")
        
        # Check enum types
        enum_res = await conn.execute(text(
            "SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid;"
        ))
        enums = enum_res.fetchall()
        print("Enums in DB:")
        for type_name, label in enums:
            print(f"  {type_name}: {label}")

if __name__ == "__main__":
    asyncio.run(probe())
