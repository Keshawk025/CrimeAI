"""
app/test_similar_cases.py
──────────────────────────
Test suite for the Similar Case Retrieval feature (Task 10).
"""

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

from app.db.base import AsyncSessionLocal
from app.models.fir import FIR, FileType
from app.db.init_db import check_db_connection
from app.services.qdrant_index_service import QdrantIndexService


async def run_tests():
    print("=== STARTING SIMILAR CASE RETRIEVAL TEST SUITE ===")
    
    # 1. Initialize database
    print("\n[Test DB] Initializing database and tables...")
    db_ok = await check_db_connection()
    if not db_ok:
        print("❌ Database connection check failed.")
        sys.exit(1)
    print("✅ Database connection check passed.")

    # Cleanup pre-existing test records from previous crashed runs
    print("🧹 Cleaning up pre-existing test records from previous crashed runs...")
    from app.services.qdrant_service import init_qdrant_client, close_qdrant_client
    await init_qdrant_client()
    async with AsyncSessionLocal() as session:
        stmt = select(FIR).where(FIR.created_by.like("%tester%"))
        res = await session.execute(stmt)
        old_firs = res.scalars().all()
        qdrant_service = QdrantIndexService()
        for old_fir in old_firs:
            try:
                storage_path = Path(old_fir.storage_path)
                if storage_path.exists():
                    storage_path.unlink()
            except Exception:
                pass
            try:
                await qdrant_service.delete_vector(old_fir.id)
            except Exception:
                pass
            await session.delete(old_fir)
        await session.commit()
    await close_qdrant_client()
    print("🧹 Cleanup complete.")

    # Start uvicorn backend server on port 8000
    print("\nStarting FastAPI server on port 8000...")
    test_env = os.environ.copy()
    test_env["ENKRYPT_ENABLED"] = "false"
    test_env["PYTHONUNBUFFERED"] = "1"
    server_process = subprocess.Popen(
        [".venv/bin/python", "-u", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
    client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=120.0)
    try:
        res = await client.get("/api/v1/health")
        print(f"Server health check: {res.status_code} {res.json()}")
    except Exception as e:
        print(f"❌ Server did not start: {e}")
        server_process.terminate()
        sys.exit(1)

    # Prepare temp files
    temp_dir = tempfile.mkdtemp()
    
    # Create 3 files representing crime reports (2 thefts, 1 murder)
    fir1_path = os.path.join(temp_dir, "fir1.txt")
    with open(fir1_path, "w") as f:
        f.write("Case No: FIR/2026/T001. A thief stole a mobile phone from Amit Patel on Indiranagar 100 feet road. The suspect Rajesh Kumar used a knife and fled on a red motorcycle.")

    fir2_path = os.path.join(temp_dir, "fir2.txt")
    with open(fir2_path, "w") as f:
        f.write("Case No: FIR/2026/T002. Theft incident at Majestic. Rajesh Kumar stole a gold chain from Amit Patel using a knife. Escaped on a vehicle.")

    fir3_path = os.path.join(temp_dir, "fir3.txt")
    with open(fir3_path, "w") as f:
        f.write("Case No: FIR/2026/M001. Murder case. Deepa Shastry was stabbed by Vijay Mallya using a pistol in Majestic. No vehicles involved.")

    fir_unindexed_path = os.path.join(temp_dir, "fir_unindexed.txt")
    with open(fir_unindexed_path, "w") as f:
        f.write("Case No: FIR/2026/U001. Unindexed crime report. Unique content for duplicate check bypass.")

    uploaded_ids = []

    async def process_case(file_path: str, case_num: str) -> str:
        # Upload
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "text/plain")}
            data = {"case_number": case_num, "created_by": "tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            if res.status_code != 201:
                print(f"❌ Upload failed with status {res.status_code}: {res.text}")
            assert res.status_code == 201
            fid = res.json()["id"]
        
        # Extract text
        await client.post(f"/api/v1/firs/{fid}/extract")
        # Extract entities
        await client.post(f"/api/v1/firs/{fid}/entities")
        # Index
        await client.post(f"/api/v1/firs/{fid}/index")
        return fid

    try:
        # Process all cases
        print("\nProcessing and indexing test cases...")
        id1 = await process_case(fir1_path, "CASE-T001")
        id2 = await process_case(fir2_path, "CASE-T002")
        id3 = await process_case(fir3_path, "CASE-M001")
        uploaded_ids.extend([id1, id2, id3])
        print(f"✅ Processed and indexed 3 cases: {id1}, {id2}, {id3}")

        # ── Test 1: Query Similarity ─────────────────────────────────────
        print("\n[Test 1] Querying similar cases for CASE-T001 (Theft)...")
        start_time = time.time()
        res_sim = await client.post(f"/api/v1/firs/{id1}/similar")
        duration = time.time() - start_time
        
        print(f"Response duration: {duration:.2f} seconds")
        assert duration < 3.0, "Response time took longer than 3 seconds!"
        assert res_sim.status_code == 200, f"Failed: {res_sim.text}"
        
        data = res_sim.json()
        print(f"Similar Cases Response: {data}")
        assert data["query_fir"] == "CASE-T001"
        assert len(data["matches"]) > 0
        
        # Verify that the query FIR itself is NOT in matches
        match_ids = [m["fir_id"] for m in data["matches"]]
        assert id1 not in match_ids, "Query FIR should not appear in its own similarity search results!"
        
        # Verify that CASE-T002 is the top match (since both are theft, Amit Patel, Rajesh Kumar, knife)
        top_match = data["matches"][0]
        assert top_match["case_number"] == "CASE-T002", f"Top match should be CASE-T002, got {top_match['case_number']}"
        print(f"Top match similarity: {top_match['similarity']}%")
        print(f"Top match reasons: {top_match['reasons']}")
        
        # Verify reasons check
        assert any("crime category" in r for r in top_match["reasons"])
        assert any("suspect" in r for r in top_match["reasons"])
        assert any("victim" in r for r in top_match["reasons"])
        assert any("weapon" in r for r in top_match["reasons"])
        print("✅ Query similarity successfully verified with rich reasoning.")

        # ── Test 2: Missing Embedding ─────────────────────────────────────
        print("\n[Test 2] Verifying error when querying a FIR with missing embedding...")
        # Upload a new case without extracting or indexing
        with open(fir_unindexed_path, "rb") as f:
            files = {"file": ("new_case.txt", f, "text/plain")}
            data = {"case_number": "CASE-UNINDEXED", "created_by": "tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            assert res.status_code == 201, f"Failed to upload unindexed case: {res.text}"
            new_id = res.json()["id"]
            uploaded_ids.append(new_id)
            
        res_bad = await client.post(f"/api/v1/firs/{new_id}/similar")
        print(f"Missing embedding response: status={res_bad.status_code}, response={res_bad.text}")
        assert res_bad.status_code == 400
        assert "has not been indexed yet" in res_bad.json()["detail"]
        print("✅ Correctly rejected query for unindexed FIR.")

    finally:
        # Clean up files from disk
        shutil.rmtree(temp_dir)
        # Terminate server
        server_process.terminate()
        # Clean up database records
        print("\nCleaning up database test records...")
        async with AsyncSessionLocal() as session:
            for fid in uploaded_ids:
                stmt = select(FIR).where(str(FIR.id) == str(fid))
                res = await session.execute(stmt)
                fir_obj = res.scalar_one_or_none()
                if fir_obj:
                    file_path = Path(fir_obj.storage_path)
                    if file_path.exists():
                        file_path.unlink()
                    await session.delete(fir_obj)
            await session.commit()
            
        # Clean up Qdrant points
        print("Cleaning up Qdrant vectors...")
        from app.services.qdrant_service import init_qdrant_client, close_qdrant_client
        await init_qdrant_client()
        qdrant_service = QdrantIndexService()
        for fid in uploaded_ids:
            try:
                await qdrant_service.delete_vector(fid)
            except Exception:
                pass
        await close_qdrant_client()
        print("✅ Database and Qdrant clean up complete.")

    # ── Test 3: Qdrant Unavailable ─────────────────────────────────────
    print("\n[Test 3] Verifying behavior when Qdrant is unavailable...")
    # Start a server instance with a bad QDRANT_URL
    bad_env = os.environ.copy()
    bad_env["ENKRYPT_ENABLED"] = "false"
    bad_env["QDRANT_URL"] = "http://127.0.0.1:54321"  # Non-existent server
    bad_env["PYTHONUNBUFFERED"] = "1"
    
    bad_server = subprocess.Popen(
        [".venv/bin/python", "-u", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        env=bad_env
    )
    
    # Wait for bad server to boot (polling)
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
        # Querying similar endpoint on bad server (since Qdrant is bad, it should return 503)
        res_bad_q = await bad_client.post(f"/api/v1/firs/{id1}/similar")
        print(f"Bad Qdrant similar response: status={res_bad_q.status_code}, response={res_bad_q.text}")
        assert res_bad_q.status_code == 503
        res_json = res_bad_q.json()
        assert "unavailable" in res_json.get("detail", "").lower() or "unavailable" in res_json.get("error", "").lower()
        print("✅ Correctly returned HTTP 503 Service Unavailable when Qdrant was unreachable.")
    finally:
        bad_server.terminate()

    print("\n=== ALL SIMILAR CASE RETRIEVAL TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
