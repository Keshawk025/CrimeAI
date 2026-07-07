import asyncio
from sqlalchemy import text
from app.db.base import engine, Base
import app.models.fir
import app.models.fir_document_content
import app.models.fir_entity
import app.models.fir_embedding

async def fix_enum():
    print("Connecting to database to drop conflicting tables and enums...")
    async with engine.begin() as conn:
        # Drop tables with cascade
        await conn.execute(text("DROP TABLE IF EXISTS fir_embeddings CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS fir_entities CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS fir_document_contents CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS firs CASCADE;"))
        print("Dropped tables: fir_embeddings, fir_entities, fir_document_contents, firs.")

        # Drop enums
        await conn.execute(text("DROP TYPE IF EXISTS fir_status;"))
        await conn.execute(text("DROP TYPE IF EXISTS filetype;"))
        print("Dropped enum types: fir_status, filetype.")

    print("Recreating database tables and enums...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database schema successfully recreated!")

if __name__ == "__main__":
    asyncio.run(fix_enum())
