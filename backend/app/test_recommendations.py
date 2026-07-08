"""
app/test_recommendations.py
───────────────────────────
Test suite for AI Investigation Recommendations (Task 14).
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
from app.models.fir import FIR
from app.db.init_db import check_db_connection


async def run_tests():
    print("=== STARTING AI INVESTIGATION RECOMMENDATIONS TEST SUITE ===")
    
    # 1. Initialize database
    print("\n[Test DB] Checking database connection...")
    db_ok = await check_db_connection()
    if not db_ok:
        print("❌ Database connection check failed.")
        sys.exit(1)
    print("✅ Database connection check passed.")

    # Start backend server
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
    
    # Robbery case file
    unique_id = str(int(time.time()))
    robbery_path = os.path.join(temp_dir, f"robbery_fir_{unique_id}.txt")
    with open(robbery_path, "w") as f:
        f.write(f"Case Number: FIR/2026/ROB-12-{unique_id}. Armed robbery reported at indiranagar jewelry store by shopowner. "
                "Suspect named Rajesh Kumar entered with pistol. Flees on vehicle KA03XY9999 bike. "
                "Witness saw him calling from mobile number +91-9988776655.")

    # Empty case file
    empty_path = os.path.join(temp_dir, f"empty_fir_{unique_id}.txt")
    with open(empty_path, "w") as f:
        f.write("Short text")

    uploaded_ids = []

    try:
        # ── Test 1: Robbery FIR Recommendations ──────────────────────────
        print("\n[Test 1] Uploading and analyzing robbery FIR...")
        with open(robbery_path, "rb") as f:
            files = {"file": (f"robbery_fir_{unique_id}.txt", f, "text/plain")}
            data = {"case_number": f"CASE-ROBBERY-{unique_id}", "created_by": "recommendation_tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            assert res.status_code == 201
            fid_rob = res.json()["id"]
            uploaded_ids.append(fid_rob)

        # Extract text and entities
        await client.post(f"/api/v1/firs/{fid_rob}/extract")
        await client.post(f"/api/v1/firs/{fid_rob}/entities")
        
        # Query recommendations
        res_rec = await client.post(f"/api/v1/firs/{fid_rob}/recommendations")
        print(f"Recommendations response code: {res_rec.status_code}")
        assert res_rec.status_code == 200
        rec_data = res_rec.json()
        assert "recommendations" in rec_data
        print(f"Found {len(rec_data['recommendations'])} recommendations:")
        for r in rec_data["recommendations"]:
            print(f" - Title: {r['title']} | Priority: {r['priority']} | Confidence: {r['confidence']}% | Category: {r['category']}")
            assert r["priority"] in ["High", "Medium", "Low"]
            assert 0 <= r["confidence"] <= 100
            assert r["category"] in ["Evidence Collection", "Witness Actions", "Location Investigation", "Suspect Investigation"]
        
        # Verify evidence categories are populated
        categories = [r["category"] for r in rec_data["recommendations"]]
        assert "Evidence Collection" in categories
        print("✅ Robbery recommendations verified successfully.")

        # ── Test 2: Short / Empty FIR ─────────────────────────────────────
        print("\n[Test 2] Uploading and analyzing empty/short FIR...")
        with open(empty_path, "rb") as f:
            files = {"file": (f"empty_fir_{unique_id}.txt", f, "text/plain")}
            data = {"case_number": f"CASE-EMPTY-{unique_id}", "created_by": "recommendation_tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            assert res.status_code == 201
            fid_empty = res.json()["id"]
            uploaded_ids.append(fid_empty)

        # Extract text
        await client.post(f"/api/v1/firs/{fid_empty}/extract")
        
        # Query recommendations
        res_rec_empty = await client.post(f"/api/v1/firs/{fid_empty}/recommendations")
        print(f"Empty recommendations response: {res_rec_empty.json()}")
        assert res_rec_empty.status_code == 200
        assert "Not enough evidence" in res_rec_empty.json().get("message", "")
        print("✅ Insufficient evidence safety rule passed.")

    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        server_process.terminate()
        
        # Clean up DB
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

    print("\n=== ALL AI RECOMMENDATIONS TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
