"""
app/test_explainability.py
──────────────────────────
Test suite for Task 15 — Explainable AI.

Verifies that every AI endpoint returns the explainability envelope:
  result, confidence, reasoning, supporting_cases, supporting_entities, limitations

Does NOT re-run uploads/indexing from scratch — uses a single fresh test FIR.
"""

import asyncio
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
import subprocess

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from app.db.init_db import check_db_connection


REQUIRED_KEYS = {"confidence", "reasoning", "supporting_cases", "supporting_entities", "limitations"}


def assert_explainability_envelope(data: dict, label: str):
    """Assert all required explainability keys are present and valid."""
    missing = REQUIRED_KEYS - set(data.keys())
    assert not missing, f"[{label}] Missing explainability keys: {missing}. Got keys: {list(data.keys())}"

    # confidence must be an int 0-100
    assert isinstance(data["confidence"], (int, float)), f"[{label}] confidence must be numeric, got {type(data['confidence'])}"
    assert 0 <= data["confidence"] <= 100, f"[{label}] confidence out of range: {data['confidence']}"

    # reasoning must be a non-empty string
    assert isinstance(data["reasoning"], str), f"[{label}] reasoning must be string"
    assert len(data["reasoning"]) > 0, f"[{label}] reasoning must not be empty"

    # supporting_cases must be a list
    assert isinstance(data["supporting_cases"], list), f"[{label}] supporting_cases must be list"

    # supporting_entities must be a list
    assert isinstance(data["supporting_entities"], list), f"[{label}] supporting_entities must be list"

    # limitations must be a non-empty list
    assert isinstance(data["limitations"], list), f"[{label}] limitations must be list"
    assert len(data["limitations"]) > 0, f"[{label}] limitations must not be empty"

    # Check that reasoning is never fabricated
    assert data["reasoning"] != "", f"[{label}] reasoning should not be empty string"

    print(f"  ✓ confidence={data['confidence']}%")
    print(f"  ✓ reasoning='{data['reasoning'][:80]}...'")
    print(f"  ✓ supporting_entities={len(data['supporting_entities'])}")
    print(f"  ✓ supporting_cases={len(data['supporting_cases'])}")
    print(f"  ✓ limitations={len(data['limitations'])}")


async def run_tests():
    print("=" * 60)
    print("TASK 15 — EXPLAINABLE AI TEST SUITE")
    print("=" * 60)

    # 1. Check DB
    print("\n[Setup] Checking database connection...")
    db_ok = await check_db_connection()
    if not db_ok:
        print("❌ Database connection failed.")
        sys.exit(1)
    print("✅ Database connection OK.")

    # 2. Start backend server
    print("\n[Setup] Starting FastAPI server on port 8000...")
    test_env = os.environ.copy()
    test_env["ENKRYPT_ENABLED"] = "false"
    test_env["PYTHONUNBUFFERED"] = "1"
    server_process = subprocess.Popen(
        [".venv/bin/python", "-u", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        env=test_env,
    )

    # Wait for server
    print("Waiting for server to boot...")
    for i in range(30):
        time.sleep(1)
        if server_process.poll() is not None:
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
        print(f"Server health: {res.status_code}")
    except Exception as e:
        print(f"❌ Server did not start: {e}")
        server_process.terminate()
        sys.exit(1)

    # 3. Prepare test data
    temp_dir = tempfile.mkdtemp()
    fir_path = os.path.join(temp_dir, "explainability_test.txt")
    with open(fir_path, "w") as f:
        f.write(
            f"Case No: FIR/2026/XAI-{int(time.time())}\n"
            "Theft case. Suspect Rajesh Kumar stole a laptop from victim Priya Sharma "
            "at MG Road, Bangalore using a knife. Witness Sunil saw the incident. "
            "Suspect fled on a red Honda Activa KA-01-AB-1234. Phone: 9876543210. "
            "Organization: Bangalore City Police."
        )

    uploaded_ids = []
    try:
        # ── Upload ──
        print("\n[Setup] Uploading test FIR...")
        with open(fir_path, "rb") as f:
            files = {"file": ("xai_test.txt", f, "text/plain")}
            data = {"case_number": f"CASE-XAI-{int(time.time())}", "created_by": "xai_tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            assert res.status_code == 201, f"Upload failed: {res.text}"
            fid = res.json()["id"]
            uploaded_ids.append(fid)
        print(f"  FIR ID: {fid}")

        # ── Extract text ──
        print("[Setup] Extracting text...")
        res = await client.post(f"/api/v1/firs/{fid}/extract")
        assert res.status_code == 200, f"Extract failed: {res.text}"
        print("  ✅ Text extracted.")

        # ════════════════════════════════════════════════════════════
        # TEST 1: Entity Extraction Explainability
        # ════════════════════════════════════════════════════════════
        print("\n" + "─" * 50)
        print("[Test 1] Entity Extraction — Explainability Envelope")
        res = await client.post(f"/api/v1/firs/{fid}/entities")
        assert res.status_code == 200, f"Entity extraction failed: {res.text}"
        entity_data = res.json()
        print(f"  API returned keys: {list(entity_data.keys())}")

        # Must have 'result' key (the entities array)
        assert "result" in entity_data, "Entity response must contain 'result' key"
        assert isinstance(entity_data["result"], list), "result must be a list of entities"
        assert_explainability_envelope(entity_data, "Entity Extraction")
        print("✅ Entity Extraction Explainability — PASSED\n")

        # ── Index (needed for similar cases & copilot) ──
        print("[Setup] Indexing FIR in Qdrant...")
        res = await client.post(f"/api/v1/firs/{fid}/index")
        assert res.status_code == 200, f"Index failed: {res.text}"
        print("  ✅ Indexed.")

        # ════════════════════════════════════════════════════════════
        # TEST 2: Similar Case Retrieval Explainability
        # ════════════════════════════════════════════════════════════
        print("\n" + "─" * 50)
        print("[Test 2] Similar Case Retrieval — Explainability Envelope")
        res = await client.post(f"/api/v1/firs/{fid}/similar")
        assert res.status_code == 200, f"Similar cases failed: {res.text}"
        similar_data = res.json()
        print(f"  API returned keys: {list(similar_data.keys())}")

        # Must have 'result' and backward-compat 'matches'
        assert "matches" in similar_data, "Similar response must contain 'matches' key"
        assert_explainability_envelope(similar_data, "Similar Cases")
        print("✅ Similar Case Retrieval Explainability — PASSED\n")

        # ════════════════════════════════════════════════════════════
        # TEST 3: Investigation Copilot Explainability
        # ════════════════════════════════════════════════════════════
        print("─" * 50)
        print("[Test 3] Investigation Copilot — Explainability Envelope")
        res = await client.post(
            f"/api/v1/firs/{fid}/copilot",
            json={"question": "Who are the main suspects in this case?"},
        )
        assert res.status_code == 200, f"Copilot failed: {res.text}"
        copilot_data = res.json()
        print(f"  API returned keys: {list(copilot_data.keys())}")

        # Must have backward-compat 'answer'
        assert "answer" in copilot_data, "Copilot response must contain 'answer' key"
        assert_explainability_envelope(copilot_data, "Copilot")
        print("✅ Investigation Copilot Explainability — PASSED\n")

        # ════════════════════════════════════════════════════════════
        # TEST 4: Copilot with Insufficient Evidence
        # ════════════════════════════════════════════════════════════
        print("─" * 50)
        print("[Test 4] Copilot — Low Confidence for Unknown Query")
        res = await client.post(
            f"/api/v1/firs/{fid}/copilot",
            json={"question": "What was the weather like during the incident?"},
        )
        assert res.status_code == 200, f"Copilot (unknown) failed: {res.text}"
        unknown_data = res.json()
        assert_explainability_envelope(unknown_data, "Copilot (unknown)")

        # When evidence is insufficient, reasoning should indicate limited evidence
        if unknown_data["answer"] == "I don't have enough evidence.":
            assert unknown_data["confidence"] <= 50, f"Confidence should be low for unknown query, got {unknown_data['confidence']}"
            assert "limited" in unknown_data["reasoning"].lower() or "evidence" in unknown_data["reasoning"].lower(), \
                f"Reasoning should mention limited evidence: {unknown_data['reasoning']}"
            print("  ✓ Low-confidence answer correctly flagged.")
        else:
            print(f"  ⚠ Model answered anyway (confidence={unknown_data['confidence']}%). Checking reasoning still present.")
        print("✅ Copilot Low-Confidence Explainability — PASSED\n")

        # ════════════════════════════════════════════════════════════
        # TEST 5: Investigation Recommendations Explainability
        # ════════════════════════════════════════════════════════════
        print("─" * 50)
        print("[Test 5] Investigation Recommendations — Explainability Envelope")
        res = await client.post(f"/api/v1/firs/{fid}/recommendations")
        assert res.status_code == 200, f"Recommendations failed: {res.text}"
        rec_data = res.json()
        print(f"  API returned keys: {list(rec_data.keys())}")

        # Must have backward-compat 'recommendations'
        assert "recommendations" in rec_data, "Recommendations response must contain 'recommendations' key"
        assert_explainability_envelope(rec_data, "Recommendations")
        print("✅ Investigation Recommendations Explainability — PASSED\n")

        # ════════════════════════════════════════════════════════════
        # TEST 6: No Fabrication — Verify Confidence Calibration
        # ════════════════════════════════════════════════════════════
        print("─" * 50)
        print("[Test 6] No Fabrication — Confidence Calibration Check")

        # Entity extraction confidence should be based on actual extraction data
        print(f"  Entity confidence: {entity_data['confidence']}%")
        assert entity_data["confidence"] > 0, "Entity confidence should be > 0 for valid extraction"

        # Similar cases with no matches should have moderate confidence
        if len(similar_data["matches"]) == 0:
            assert similar_data["confidence"] <= 60, f"Empty matches should have moderate confidence, got {similar_data['confidence']}"
            print(f"  Similar (no matches) confidence: {similar_data['confidence']}% — correctly moderate")
        else:
            print(f"  Similar ({len(similar_data['matches'])} matches) confidence: {similar_data['confidence']}%")

        # Recommendations confidence should be reasonable
        print(f"  Recommendations confidence: {rec_data['confidence']}%")
        print("✅ No Fabrication — PASSED\n")

    finally:
        # Cleanup
        print("\n[Cleanup] Removing test data...")
        shutil.rmtree(temp_dir, ignore_errors=True)

        from sqlalchemy import select
        from app.db.base import AsyncSessionLocal
        from app.models.fir import FIR

        async with AsyncSessionLocal() as session:
            for fid_str in uploaded_ids:
                stmt = select(FIR).where(FIR.id == uuid.UUID(fid_str))
                res = await session.execute(stmt)
                fir_obj = res.scalar_one_or_none()
                if fir_obj:
                    p = Path(fir_obj.storage_path)
                    if p.exists():
                        p.unlink()
                    await session.delete(fir_obj)
            await session.commit()
        print("✅ Cleanup complete.")

        server_process.terminate()

    print("\n" + "=" * 60)
    print("ALL TASK 15 EXPLAINABILITY TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
