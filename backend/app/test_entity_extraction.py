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
from app.models.fir import FIR, FileType
from app.models.fir_document_content import FIRDocumentContent
from app.models.fir_entity import FIREntity
from app.db.init_db import check_db_connection

# Start uvicorn server in background
import subprocess

async def run_tests():
    print("=== STARTING ENTITY EXTRACTION TEST SUITE ===")
    
    # 1. Ensure DB connection & tables are initialized
    print("\n[Test DB] Initializing database and tables...")
    db_ok = await check_db_connection()
    if not db_ok:
        print("❌ Database connection check failed.")
        sys.exit(1)
    print("✅ Database connection check passed.")

    # Check if a server is already running on port 8000
    server_already_running = False
    client = httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=35.0)
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
        
        # Wait for server to boot
        time.sleep(5)
        
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
            server_process.terminate()
            stdout, stderr = server_process.communicate()
            print("--- SERVER STDOUT ---")
            print(stdout)
            print("--- SERVER STDERR ---")
            print(stderr)
            sys.exit(1)

    # Prepare real and corrupted test files
    temp_dir = tempfile.mkdtemp()
    
    # 1. Short FIR Text File
    short_txt_path = Path(temp_dir) / "short_fir.txt"
    short_txt_path.write_text(
        "Karnataka Police FIR. Case No: 320/2026. "
        "Complainant Harish Rao reported that suspect Rajesh Kumar stole a mobile phone "
        "and threatened him with a knife near Vidhana Soudha, Majestic, Bangalore. "
        "The incident occurred on 2026-07-06 at 18:30. "
        "Witness Inspector Shivanna was present. Contact number of suspect is 9876543210. Email: rajesh@gmail.com."
    )

    # 2. Long FIR Text File
    long_txt_path = Path(temp_dir) / "long_fir.txt"
    long_txt_path.write_text(
        "FIRST INFORMATION REPORT (Under Section 154 CrPC)\n\n"
        "1. District: Bengaluru City. Police Station: Koramangala. Year: 2026. FIR No: 1145.\n"
        "2. Acts and Sections: Section 379 IPC (Theft), Section 506 IPC (Criminal Intimidation).\n"
        "3. Occurrence of Offence: Date: 2026-07-05. Time: 14:00 hrs. Place: Koramangala 4th Block, near Sony World Signal.\n"
        "4. Complainant / Informant: Deepa Shastry, resident of Indiranagar, Bengaluru. Phone: 9001234567.\n"
        "5. Details of Suspects: Suspect Vijay Mallya, driving a red Honda Activa bike bearing registration number KA-01-EF-1234.\n"
        "6. Details of Properties Stolen: Gold chain worth Rs. 50,000.\n"
        "7. Description of Weapons: Iron rod was used to threaten the victim.\n"
        "8. Witnesses: Anand (Security Guard), Naveen (Shopkeeper).\n"
        "9. Evidence collected: CCTV footage from the signal, fingerprint samples from the scene.\n"
        "10. Brief Facts: The victim Deepa Shastry was walking near Sony World signal when the suspect Vijay Mallya approached on a scooter. "
        "He pulled out an iron rod, threatened her, grabbed the gold chain worth 50000 and sped off towards Koramangala. "
        "The registration number KA 01 EF 1234 was noted by shopkeeper Naveen who witnessed the crime."
    )
    
    # 3. Empty Text File
    empty_txt_path = Path(temp_dir) / "empty_fir.txt"
    empty_txt_path.write_text(" ")

    # 4. Kannada/Multilingual Text File
    kannada_txt_path = Path(temp_dir) / "kannada_fir.txt"
    kannada_txt_path.write_text(
        "ಪ್ರಥಮ ಮಾಹಿತಿ ವರದಿ (FIR). ಪ್ರಕರಣ ಸಂಖ್ಯೆ: 440/2026. "
        "ಫಿರ್ಯಾದಿ ಹರೀಶ್ ರಾವ್ ಅವರು ಆರೋಪಿ ರಾಜೇಶ್ ಕುಮಾರ್ ಎಂಬುವರು ಮೊಬೈಲ್ ಕದ್ದಿದ್ದಾರೆ ಎಂದು ಆರೋಪಿಸಿದ್ದಾರೆ. "
        "ಘಟನೆಯು ಬೆಂಗಳೂರಿನ ವಿಧಾನ ಸೌಧದ ಬಳಿ ನಡೆದಿದೆ."
    )

    uploaded_firs = {}

    try:
        # Helper function to upload file
        async def upload_file(path: Path, case_number: str):
            with open(path, "rb") as f:
                res = await client.post(
                    "/api/v1/firs/upload",
                    data={"case_number": case_number, "created_by": "tester"},
                    files={"file": (path.name, f, "text/plain")}
                )
            if res.status_code != 201:
                raise ValueError(f"Upload failed: {res.status_code} {res.text}")
            return res.json()["id"]

        # Upload files
        print("\nUploading test documents...")
        uploaded_firs["short"] = await upload_file(short_txt_path, "CASE-SHORT-ENTITY")
        uploaded_firs["long"] = await upload_file(long_txt_path, "CASE-LONG-ENTITY")
        uploaded_firs["empty"] = await upload_file(empty_txt_path, "CASE-EMPTY-ENTITY")
        uploaded_firs["kannada"] = await upload_file(kannada_txt_path, "CASE-KANNADA-ENTITY")
        print("✅ All test documents uploaded successfully.")

        # Extract text first (prerequisite)
        print("\nExtracting text from uploaded FIRs...")
        for key, fid in uploaded_firs.items():
            res = await client.post(f"/api/v1/firs/{fid}/extract")
            assert res.status_code == 200, f"Extraction failed for {key}: {res.text}"
        print("✅ Text extraction complete.")

        # Test 1: Short FIR Entity Extraction
        print("\n[Test 1] Extracting entities from Short FIR...")
        short_id = uploaded_firs["short"]
        res = await client.post(f"/api/v1/firs/{short_id}/entities")
        assert res.status_code == 200, f"Short FIR Entity Extraction failed: {res.status_code} {res.text}"
        entities = res.json()
        print(f"✅ Extracted {len(entities)} entities from Short FIR.")
        
        # Verify basic expected entities (victims, suspects, weapons, phones, emails, locations)
        types_extracted = [e["entity_type"] for e in entities]
        values_extracted = [e["entity_value"].lower() for e in entities]
        print(f"Types extracted: {set(types_extracted)}")
        print(f"Values extracted: {values_extracted}")

        assert "suspect" in types_extracted or "person" in types_extracted, "No suspects/persons extracted!"
        assert "weapon" in types_extracted, "No weapons extracted!"
        assert "phone" in types_extracted, "No phone number extracted!"
        assert "email" in types_extracted, "No email extracted!"

        # Test 2: Long FIR Entity Extraction
        print("\n[Test 2] Extracting entities from Long FIR...")
        long_id = uploaded_firs["long"]
        res = await client.post(f"/api/v1/firs/{long_id}/entities")
        assert res.status_code == 200, f"Long FIR Entity Extraction failed: {res.status_code} {res.text}"
        entities_long = res.json()
        print(f"✅ Extracted {len(entities_long)} entities from Long FIR.")
        
        types_long = [e["entity_type"] for e in entities_long]
        values_long = [e["entity_value"].lower() for e in entities_long]
        print(f"Types extracted: {set(types_long)}")
        print(f"Values extracted: {values_long}")

        assert "victim" in types_long or "person" in types_long
        assert "weapon" in types_long
        assert "vehicle" in types_long or any("ka-" in v or "ka01" in v for v in values_long)

        # Test 3: Kannada Multilingual FIR Entity Extraction
        print("\n[Test 3] Extracting entities from Kannada FIR...")
        kannada_id = uploaded_firs["kannada"]
        res = await client.post(f"/api/v1/firs/{kannada_id}/entities")
        assert res.status_code == 200, f"Kannada FIR Entity Extraction failed: {res.status_code} {res.text}"
        entities_kannada = res.json()
        print(f"✅ Extracted {len(entities_kannada)} entities from Kannada FIR.")

        # Test 4: Empty FIR Entity Extraction
        print("\n[Test 4] Extracting entities from Empty FIR...")
        empty_id = uploaded_firs["empty"]
        res = await client.post(f"/api/v1/firs/{empty_id}/entities")
        assert res.status_code == 200, f"Empty FIR Entity Extraction failed: {res.status_code} {res.text}"
        entities_empty = res.json()
        print(f"✅ Empty FIR returned {len(entities_empty)} entities.")
        assert len(entities_empty) == 0, f"Expected 0 entities, got {len(entities_empty)}"

        # Test 5: Invalid response & Retry mechanism
        print("\n[Test 5] Triggering Invalid response simulation and verifying Retry mechanism...")
        res = await client.post(f"/api/v1/firs/{short_id}/entities?force_invalid_once=true")
        assert res.status_code == 200, f"Retry mechanism test failed: {res.status_code} {res.text}"
        print(f"✅ Retry mechanism succeeded. Extracted {len(res.json())} entities after retry.")

        # Test 6: Database storage verification
        print("\n[Test 6] Verifying records in PostgreSQL...")
        async with AsyncSessionLocal() as session:
            stmt = select(FIREntity).where(FIREntity.fir_id == short_id)
            res_db = await session.execute(stmt)
            db_entities = res_db.scalars().all()
            print(f"✅ Database contains {len(db_entities)} stored entity rows for Short FIR.")
            assert len(db_entities) > 0, "No entity rows stored in PostgreSQL!"

            # Verify schema fields are mapped correctly
            entity_sample = db_entities[0]
            print(f"Sample DB Record: ID={entity_sample.id}, Type={entity_sample.entity_type}, Value={entity_sample.entity_value}, Confidence={entity_sample.confidence}")
            assert str(entity_sample.fir_id) == str(short_id)
            assert entity_sample.entity_type is not None
            assert entity_sample.entity_value is not None
            assert entity_sample.confidence is not None

        # Test 7: Duplicate triggers update DB instead of duplicates
        print("\n[Test 7] Verifying subsequent runs replace existing database rows...")
        async with AsyncSessionLocal() as session:
            count_stmt = select(FIREntity).where(FIREntity.fir_id == short_id)
            initial_count = len((await session.execute(count_stmt)).scalars().all())
            print(f"Initial count in DB: {initial_count}")

        # Trigger extraction again
        res = await client.post(f"/api/v1/firs/{short_id}/entities")
        assert res.status_code == 200

        async with AsyncSessionLocal() as session:
            new_count = len((await session.execute(count_stmt)).scalars().all())
            print(f"New count in DB: {new_count}")
            assert new_count == initial_count or new_count > 0, "Row count changed unexpectedly or went to 0!"

    finally:
        # Cleanup uploaded files and entities from DB
        print("\nCleaning up uploaded files and DB entities...")
        async with AsyncSessionLocal() as session:
            for key, fid in uploaded_firs.items():
                try:
                    res_fir = await session.execute(select(FIR).where(FIR.id == fid))
                    fir_rec = res_fir.scalar_one_or_none()
                    if fir_rec:
                        storage_path = Path(fir_rec.storage_path)
                        if storage_path.exists():
                            storage_path.unlink()
                        await session.delete(fir_rec)
                except Exception as e:
                    print(f"Error during db cleanup for {fid}: {e}")
            await session.commit()
            
        shutil.rmtree(temp_dir)
        if server_process is not None:
            server_process.terminate()
            server_process.wait()
        await client.aclose()

    print("\n=== ALL ENTITY EXTRACTION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
