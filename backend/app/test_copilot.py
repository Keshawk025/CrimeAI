"""
app/test_copilot.py
────────────────────
Test suite for the AI Investigation Copilot (Task 11).
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
import uuid
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.models.fir import FIR
from app.db.init_db import check_db_connection


async def run_tests():
    print("=== STARTING AI INVESTIGATION COPILOT TEST SUITE ===")
    
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
        stdout=sys.stdout,
        stderr=sys.stderr,
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
    fir_path = os.path.join(temp_dir, "theft_fir.txt")
    with open(fir_path, "w") as f:
        f.write(f"Case No: FIR/2026/COP-01. Indiranagar robbery incident. Suspect Rajesh Kumar snatched a gold chain using a knife from Amit Patel. Vehicle involved was black bike. Timestamp: {time.time()}")

    uploaded_ids = []

    try:
        # Upload
        print("\nUploading test FIR...")
        with open(fir_path, "rb") as f:
            files = {"file": ("theft_fir.txt", f, "text/plain")}
            data = {"case_number": "CASE-COPILOT-01", "created_by": "copilot_tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            assert res.status_code == 201, f"Upload failed: {res.text}"
            fid = res.json()["id"]
            uploaded_ids.append(fid)

        # Extract text and entities
        await client.post(f"/api/v1/firs/{fid}/extract")
        await client.post(f"/api/v1/firs/{fid}/entities")
        await client.post(f"/api/v1/firs/{fid}/index")
        print(f"✅ Processed test FIR {fid}")

        # ── Test 1: Summarize FIR ─────────────────────────────────────────
        print("\n[Test 1] Query: Summarize the case...")
        res_sum = await client.post(f"/api/v1/firs/{fid}/copilot", json={"question": "Please summarize this FIR report."})
        print(f"Summary response: {res_sum.status_code} -> {res_sum.json()}")
        assert res_sum.status_code == 200
        data = res_sum.json()
        assert "answer" in data
        assert len(data["sources"]) > 0
        assert "extracted_text" in data["sources"]
        assert data["confidence"] > 70
        print("✅ Summary test passed.")

        # ── Test 2: Suspect Question ──────────────────────────────────────
        print("\n[Test 2] Query: Who is the suspect?")
        res_sus = await client.post(f"/api/v1/firs/{fid}/copilot", json={"question": "Who are the suspects?"})
        print(f"Suspect response: {res_sus.json()}")
        assert res_sus.status_code == 200
        data = res_sus.json()
        assert "Rajesh Kumar" in data["answer"]
        assert "fir_entities" in data["sources"]
        print("✅ Suspect test passed.")

        # ── Test 3: Unknown / Hallucination Safety ────────────────────────
        print("\n[Test 3] Query: What did they eat for breakfast?")
        res_unk = await client.post(f"/api/v1/firs/{fid}/copilot", json={"question": "What did they eat for breakfast?"})
        print(f"Unknown response: {res_unk.json()}")
        assert res_unk.status_code == 200
        data = res_unk.json()
        assert data["answer"] == "I don't have enough evidence."
        print("✅ Hallucination safety test passed.")

        # ── Test 4: Missing FIR Error Handling ────────────────────────────
        print("\n[Test 4] Query: Asking copilot on non-existent FIR ID...")
        bad_fid = str(uuid.uuid4())
        res_bad = await client.post(f"/api/v1/firs/{bad_fid}/copilot", json={"question": "Summarize this case."})
        print(f"Missing FIR response: {res_bad.status_code} -> {res_bad.text}")
        assert res_bad.status_code in (400, 404)
        assert "not found" in res_bad.json()["detail"].lower()
        print("✅ Missing FIR handled correctly.")

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

    print("\n=== ALL AI INVESTIGATION COPILOT TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
