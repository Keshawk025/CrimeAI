import asyncio
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.models.fir import FIR, FileType, FIRStatus
from app.db.init_db import check_db_connection

# Start uvicorn server in background
import subprocess

async def run_tests():
    print("=== STARTING TEST SUITE ===")
    
    # 1. Ensure DB connection & tables are initialized
    print("\n[Test 1] Initializing database and tables...")
    db_ok = await check_db_connection()
    if not db_ok:
        print("❌ Database connection check failed.")
        sys.exit(1)
    print("✅ Database connection check passed.")

    # Check if a server is already running on port 8000
    server_already_running = False
    client = httpx.AsyncClient(base_url="http://127.0.0.1:8000")
    try:
        res = await client.get("/api/v1/health")
        if res.status_code == 200:
            print("🚀 Detected that a FastAPI backend server is already running on port 8000. Reusing it.")
            server_already_running = True
    except Exception:
        pass

    server_process = None
    if not server_already_running:
        # Start uvicorn backend server on port 8000
        print("\nStarting FastAPI server...")
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
                # Use synchronous request for quick check
                res = httpx.get("http://127.0.0.1:8000/api/v1/health")
                if res.status_code == 200:
                    break
            except Exception:
                pass
        
        # Check if the process exited immediately
        poll_status = server_process.poll()
        if poll_status is not None:
            print(f"❌ Server process exited immediately with code {poll_status}")
            stdout, stderr = server_process.communicate()
            print("--- SERVER STDOUT ---")
            print(stdout)
            print("--- SERVER STDERR ---")
            print(stderr)
            sys.exit(1)
            
        # Verify health
        try:
            res = await client.get("/api/v1/health")
            print(f"Server health check: {res.status_code} {res.json()}")
        except Exception as e:
            print(f"❌ Server failed to start: {e}")
            # Terminate first so communicate() returns immediately
            server_process.terminate()
            stdout, stderr = server_process.communicate()
            print("--- SERVER STDOUT ---")
            print(stdout)
            print("--- SERVER STDERR ---")
            print(stderr)
            sys.exit(1)

    # Prepare dummy test files
    temp_dir = tempfile.mkdtemp()
    
    txt_path = Path(temp_dir) / "test_fir.txt"
    txt_path.write_text("This is a test FIR TXT content.")
    
    pdf_path = Path(temp_dir) / "test_fir.pdf"
    pdf_path.write_text("This is a dummy PDF content.")
    
    docx_path = Path(temp_dir) / "test_fir.docx"
    docx_path.write_text("This is a dummy DOCX content.")
    
    invalid_path = Path(temp_dir) / "test_fir.png"
    invalid_path.write_text("dummy image data")
    
    large_path = Path(temp_dir) / "large_fir.txt"
    # Create a 21MB file
    with open(large_path, "wb") as f:
        f.write(b"0" * (21 * 1024 * 1024))

    fir_ids = []

    try:
        # Test 1: Upload PDF
        print("\n[Test 1] Upload PDF...")
        with open(pdf_path, "rb") as f:
            res = await client.post(
                "/api/v1/firs/upload",
                data={"case_number": "CASE-PDF-001", "created_by": "tester"},
                files={"file": ("test_fir.pdf", f, "application/pdf")}
            )
        assert res.status_code == 201, f"Failed: {res.status_code} {res.text}"
        data = res.json()
        fir_ids.append(data["id"])
        print(f"✅ PDF Uploaded: {data}")

        # Test 2: Upload DOCX
        print("\n[Test 2] Upload DOCX...")
        with open(docx_path, "rb") as f:
            res = await client.post(
                "/api/v1/firs/upload",
                data={"case_number": "CASE-DOCX-002", "created_by": "tester"},
                files={"file": ("test_fir.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
        assert res.status_code == 201, f"Failed: {res.status_code} {res.text}"
        data = res.json()
        fir_ids.append(data["id"])
        print(f"✅ DOCX Uploaded: {data}")

        # Test 3: Upload TXT
        print("\n[Test 3] Upload TXT...")
        with open(txt_path, "rb") as f:
            res = await client.post(
                "/api/v1/firs/upload",
                data={"case_number": "CASE-TXT-003", "created_by": "tester"},
                files={"file": ("test_fir.txt", f, "text/plain")}
            )
        assert res.status_code == 201, f"Failed: {res.status_code} {res.text}"
        data = res.json()
        fir_ids.append(data["id"])
        print(f"✅ TXT Uploaded: {data}")

        # Test 4: Duplicate upload
        print("\n[Test 4] Duplicate upload...")
        with open(txt_path, "rb") as f:
            res = await client.post(
                "/api/v1/firs/upload",
                data={"case_number": "CASE-TXT-003", "created_by": "tester"},
                files={"file": ("test_fir.txt", f, "text/plain")}
            )
        assert res.status_code == 422, f"Expected 422, got: {res.status_code} {res.text}"
        print(f"✅ Duplicate upload blocked correctly: {res.json()}")

        # Test 5: Invalid file type
        print("\n[Test 5] Invalid file type...")
        with open(invalid_path, "rb") as f:
            res = await client.post(
                "/api/v1/firs/upload",
                data={"case_number": "CASE-PNG-004", "created_by": "tester"},
                files={"file": ("test_fir.png", f, "image/png")}
            )
        assert res.status_code == 422, f"Expected 422, got: {res.status_code} {res.text}"
        print(f"✅ Invalid file type blocked correctly: {res.json()}")

        # Test 6: File larger than 20MB
        print("\n[Test 6] File larger than 20MB...")
        with open(large_path, "rb") as f:
            res = await client.post(
                "/api/v1/firs/upload",
                data={"case_number": "CASE-LARGE-005", "created_by": "tester"},
                files={"file": ("large_fir.txt", f, "text/plain")}
            )
        assert res.status_code == 422, f"Expected 422, got: {res.status_code} {res.text}"
        print(f"✅ File larger than 20MB blocked correctly: {res.json()}")

        # Test 7: List uploaded FIRs
        print("\n[Test 7] List uploaded FIRs...")
        res = await client.get("/api/v1/firs")
        assert res.status_code == 200, f"Failed: {res.status_code} {res.text}"
        list_data = res.json()
        print(f"✅ Listing successful. Total: {list_data['total']}, Items count: {len(list_data['items'])}")
        assert list_data["total"] >= 3, "Expected at least 3 uploaded FIRs in list"

        # Test 9: Verify metadata exists in PostgreSQL & file exists on disk
        print("\n[Test 9 & 10] Verify metadata and file locations...")
        async with AsyncSessionLocal() as session:
            for fid in fir_ids:
                stmt = select(FIR).where(FIR.id == fid)
                res_db = await session.execute(stmt)
                fir_record = res_db.scalar_one_or_none()
                assert fir_record is not None, f"Metadata not found in DB for ID: {fid}"
                print(f"  - DB record found: Case={fir_record.case_number}, Path={fir_record.storage_path}")
                assert Path(fir_record.storage_path).exists(), f"File does not exist on disk: {fir_record.storage_path}"
                print(f"  - Disk file verified: {fir_record.storage_path}")

        # Test 8: Delete FIR
        print("\n[Test 8] Delete FIR...")
        del_id = fir_ids[0]
        res = await client.delete(f"/api/v1/firs/{del_id}")
        assert res.status_code == 200, f"Failed deletion: {res.status_code} {res.text}"
        print(f"✅ Delete successful: {res.json()}")
        
        # Verify it is deleted from DB and disk
        async with AsyncSessionLocal() as session:
            stmt = select(FIR).where(FIR.id == del_id)
            res_db = await session.execute(stmt)
            fir_record = res_db.scalar_one_or_none()
            assert fir_record is None, f"Record still exists in DB after deletion!"
            print("  - Verified deleted from DB")

    finally:
        # Cleanup temp dir
        shutil.rmtree(temp_dir)
        # Terminate server
        if server_process is not None:
            server_process.terminate()
            server_process.wait()
        await client.aclose()

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
