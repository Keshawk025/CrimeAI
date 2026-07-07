import asyncio
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
import subprocess

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.models.fir import FIR, FileType
from app.models.fir_document_content import FIRDocumentContent
from app.models.fir_entity import FIREntity
from app.models.fir_embedding import FIREmbedding
from app.db.init_db import check_db_connection
from app.services.qdrant_index_service import QdrantIndexService


async def run_tests():
    print("=== STARTING EMBEDDING & QDRANT STORAGE TEST SUITE ===")
    
    # 1. Ensure DB connection & tables are initialized
    print("\n[Test DB] Initializing database and tables...")
    db_ok = await check_db_connection()
    if not db_ok:
        print("❌ Database connection check failed.")
        sys.exit(1)
    print("✅ Database connection check passed.")

    # Start uvicorn backend server on port 8000
    print("\nStarting FastAPI server on port 8000...")
    test_env = os.environ.copy()
    test_env["ENKRYPT_ENABLED"] = "false"
    test_env["PYTHONUNBUFFERED"] = "1"
    server_process = subprocess.Popen(
        [".venv/bin/python", "-u", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=test_env
    )
    
    # Wait for server to boot (polling)
    print("Waiting for server to boot...")
    for i in range(30):
        time.sleep(1)
        poll_status = server_process.poll()
        if poll_status is not None:
            break
        try:
            res = httpx.get("http://127.0.0.1:8000/api/v1/health")
            if res.status_code == 200:
                break
        except Exception:
            pass
    
    # Verify health
    client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=35.0)
    try:
        res = await client.get("/api/v1/health")
        print(f"Server health check: {res.status_code} {res.json()}")
    except Exception as e:
        print(f"❌ Server did not start: {e}")
        server_process.terminate()
        sys.exit(1)

    # Prepare temp files
    temp_dir = tempfile.mkdtemp()
    
    small_txt_path = os.path.join(temp_dir, "small_fir.txt")
    with open(small_txt_path, "w") as f:
        f.write("Case No: FIR/2026/A101. Suspect Suresh steals mobile from victim Harish on Indiranagar 100 feet road using a knife.")
        
    large_txt_path = os.path.join(temp_dir, "large_fir.txt")
    with open(large_txt_path, "w") as f:
        # Create a large text document (> 1000 chars)
        f.write("Case No: FIR/2026/A999. Description:\n" + ("This is a very long crime report details description that goes on and on to test large document handling. " * 30))

    uploaded_firs = {}

    async def upload_file(file_path: str, case_num: str) -> str:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "text/plain")}
            data = {"case_number": case_num, "created_by": "tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            assert res.status_code == 201, f"Failed upload: {res.text}"
            return res.json()["id"]

    try:
        # Upload documents
        print("\n[Upload] Uploading test documents...")
        small_id = await upload_file(small_txt_path, "CASE-EMB-SMALL")
        large_id = await upload_file(large_txt_path, "CASE-EMB-LARGE")
        print(f"✅ Uploaded Small FIR (ID: {small_id}) and Large FIR (ID: {large_id}).")

        # ── Test 1: Missing Extracted Text ──────────────────────────────
        print("\n[Test 1] Verifying error when attempting to index document with missing extracted text...")
        index_res = await client.post(f"/api/v1/firs/{small_id}/index")
        print(f"Index response for un-extracted text: status={index_res.status_code}, response={index_res.text}")
        assert index_res.status_code == 400
        assert "text content has not been extracted" in index_res.json()["detail"]
        print("✅ Correctly rejected indexing request due to missing extracted text.")

        # Extract text for small and large FIRs
        print("\n[Extraction] Extracting text for Small and Large FIRs...")
        await client.post(f"/api/v1/firs/{small_id}/extract")
        await client.post(f"/api/v1/firs/{large_id}/extract")
        # Also extract entities for small FIR to populate payload summary
        await client.post(f"/api/v1/firs/{small_id}/entities")
        print("✅ Text and entities extracted.")

        # ── Test 2: Indexing Small FIR ──────────────────────────────────
        print("\n[Test 2] Indexing Small FIR...")
        index_res = await client.post(f"/api/v1/firs/{small_id}/index")
        print(f"Index response: status={index_res.status_code}, data={index_res.json()}")
        assert index_res.status_code == 200
        data = index_res.json()
        assert data["fir_id"] == small_id
        assert data["vector_dimension"] == 768
        assert data["embedding_model"] is not None

        # Verify Qdrant Payload
        print("Verifying Qdrant storage...")
        qdrant_service = QdrantIndexService()
        payload = await qdrant_service.get_vector_metadata(small_id)
        print(f"Qdrant Point Payload: {payload}")
        assert payload is not None
        assert payload["fir_id"] == small_id
        assert payload["case_number"] == "CASE-EMB-SMALL"
        assert payload["extracted_text_preview"] is not None
        assert "Suresh" in payload["entity_summary"] or "Harish" in payload["entity_summary"] or "No entities" not in payload["entity_summary"]

        # Verify database metadata
        print("Verifying PostgreSQL database record...")
        async with AsyncSessionLocal() as session:
            stmt = select(FIREmbedding).where(str(FIREmbedding.fir_id) == str(small_id))
            db_res = await session.execute(stmt)
            db_emb = db_res.scalar_one_or_none()
            assert db_emb is not None
            assert str(db_emb.fir_id) == small_id
            assert db_emb.vector_dimension == 768
            print(f"PostgreSQL Row: ID={db_emb.id}, Model={db_emb.embedding_model}, Dimension={db_emb.vector_dimension}")
        print("✅ Small FIR successfully indexed in Qdrant and database.")

        # ── Test 3: Indexing Large FIR ──────────────────────────────────
        print("\n[Test 3] Indexing Large FIR...")
        index_res = await client.post(f"/api/v1/firs/{large_id}/index")
        assert index_res.status_code == 200
        large_payload = await qdrant_service.get_vector_metadata(large_id)
        assert large_payload is not None
        assert len(large_payload["extracted_text_preview"]) <= 1000
        print(f"Large FIR payload preview length: {len(large_payload['extracted_text_preview'])}")
        print("✅ Large FIR successfully indexed. Preview correctly truncated to 1000 characters.")

        # ── Test 4: Duplicate Indexing ──────────────────────────────────
        print("\n[Test 4] Re-indexing Small FIR to verify upsert behavior...")
        index_res = await client.post(f"/api/v1/firs/{small_id}/index")
        assert index_res.status_code == 200
        
        # Verify only 1 row exists in database
        async with AsyncSessionLocal() as session:
            stmt = select(FIREmbedding).where(str(FIREmbedding.fir_id) == str(small_id))
            db_res = await session.execute(stmt)
            rows = db_res.scalars().all()
            assert len(rows) == 1
            print(f"PostgreSQL row count for fir_id: {len(rows)} (Upsert successful)")
        print("✅ Duplicate indexing replaced existing metadata row and updated Qdrant vector successfully.")

    finally:
        # Clean up files from disk
        shutil.rmtree(temp_dir)
        # Terminate server
        server_process.terminate()
        # Clean up database records
        print("\nCleaning up database test records...")
        async with AsyncSessionLocal() as session:
            # Delete uploads
            for fid in [small_id, large_id]:
                stmt = select(FIR).where(str(FIR.id) == str(fid))
                res = await session.execute(stmt)
                fir_obj = res.scalar_one_or_none()
                if fir_obj:
                    # Clean up local file if created
                    file_path = Path(fir_obj.storage_path)
                    if file_path.exists():
                        file_path.unlink()
                    await session.delete(fir_obj)
            await session.commit()
            
        # Clean up Qdrant points
        print("Cleaning up Qdrant vectors...")
        for fid in [small_id, large_id]:
            try:
                await qdrant_service.delete_vector(fid)
            except Exception:
                pass
        print("✅ Database and Qdrant clean up complete.")

    # ── Test 5: Qdrant Unavailable ──────────────────────────────────
    print("\n[Test 5] Verifying behavior when Qdrant is unavailable...")
    # Start a server instance with a bad QDRANT_URL
    bad_env = os.environ.copy()
    bad_env["ENKRYPT_ENABLED"] = "false"
    bad_env["QDRANT_URL"] = "http://127.0.0.1:54321"  # Non-existent server
    bad_env["PYTHONUNBUFFERED"] = "1"
    
    bad_server = subprocess.Popen(
        [".venv/bin/python", "-u", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=bad_env
    )
    # Wait for server to boot (polling)
    print("Waiting for bad server to boot...")
    for i in range(30):
        time.sleep(1)
        poll_status = bad_server.poll()
        if poll_status is not None:
            break
        try:
            res = httpx.get("http://127.0.0.1:8001/api/v1/health")
            if res.status_code == 200:
                break
        except Exception:
            pass
    
    bad_client = httpx.AsyncClient(base_url="http://127.0.0.1:8001", timeout=10.0)
    try:
        # Upload a dummy file to bad server
        temp_dir = tempfile.mkdtemp()
        dummy_path = os.path.join(temp_dir, "dummy.txt")
        with open(dummy_path, "w") as f:
            f.write("Dummy text for testing Qdrant connection failure.")
            
        with open(dummy_path, "rb") as f:
            files = {"file": ("dummy.txt", f, "text/plain")}
            data = {"case_number": "CASE-BAD-QDRANT", "created_by": "tester"}
            res = await bad_client.post("/api/v1/firs/upload", data=data, files=files)
            dummy_id = res.json()["id"]

        # Extract text
        await bad_client.post(f"/api/v1/firs/{dummy_id}/extract")
        
        # Trigger index (this should fail when connecting to Qdrant)
        index_res = await bad_client.post(f"/api/v1/firs/{dummy_id}/index")
        print(f"Bad Qdrant index response: status={index_res.status_code}, response={index_res.text}")
        assert index_res.status_code == 503
        assert "ServiceUnavailableException" in index_res.json()["error"]
        
        # Clean up database row on bad server
        async with AsyncSessionLocal() as session:
            stmt = select(FIR).where(str(FIR.id) == str(dummy_id))
            res = await session.execute(stmt)
            fir_obj = res.scalar_one_or_none()
            if fir_obj:
                file_path = Path(fir_obj.storage_path)
                if file_path.exists():
                    file_path.unlink()
                await session.delete(fir_obj)
            await session.commit()
            
        shutil.rmtree(temp_dir)
        print("✅ Correctly returned HTTP 503 Service Unavailable when Qdrant was unreachable.")
    finally:
        bad_server.terminate()

    print("\n=== ALL EMBEDDING & INDEXING TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
