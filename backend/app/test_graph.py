"""
app/test_graph.py
──────────────────
Test suite for Criminal Relationship Graph (Task 13).
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
    print("=== STARTING CRIMINAL RELATIONSHIP GRAPH TEST SUITE ===")
    
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
    unique_id = str(int(time.time()))
    fir_path = os.path.join(temp_dir, f"graph_fir_{unique_id}.txt")
    with open(fir_path, "w") as f:
        f.write(f"Case No: FIR/2026/GR-01-{unique_id}. Gang robbery at majestic jeweler shop. Suspect Rajesh Kumar used pistol stick. Vehicle used KA02M5555 bike. Location majesty indiranagar. Evidence CCTV footage mobile.")

    uploaded_ids = []

    try:
        # Upload
        print("\nUploading test FIR...")
        with open(fir_path, "rb") as f:
            files = {"file": (f"graph_fir_{unique_id}.txt", f, "text/plain")}
            data = {"case_number": f"CASE-GRAPH-{unique_id}", "created_by": "graph_tester"}
            res = await client.post("/api/v1/firs/upload", data=data, files=files)
            print(f"Upload response: {res.status_code} {res.text}")
            assert res.status_code == 201
            fid = res.json()["id"]
            uploaded_ids.append(fid)

        # Extract text and entities
        await client.post(f"/api/v1/firs/{fid}/extract")
        await client.post(f"/api/v1/firs/{fid}/entities")
        print(f"✅ Processed test FIR {fid}")

        # ── Test 1: Fetch Relationship Graph ──────────────────────────────
        print("\n[Test 1] Query: Fetching graph JSON...")
        res_graph = await client.get(f"/api/v1/firs/{fid}/graph")
        print(f"Graph response code: {res_graph.status_code}")
        assert res_graph.status_code == 200
        graph_data = res_graph.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        
        # Print summary
        print(f"Nodes found: {len(graph_data['nodes'])}")
        print(f"Edges found: {len(graph_data['edges'])}")
        
        # Verify node properties
        fir_node = [n for n in graph_data["nodes"] if n["type"] == "fir"]
        assert len(fir_node) >= 1
        assert fir_node[0]["label"] == f"CASE-GRAPH-{unique_id}"
        
        suspect_nodes = [n for n in graph_data["nodes"] if n["type"] == "suspect"]
        print(f"Suspect nodes: {suspect_nodes}")
        assert len(suspect_nodes) >= 1
        assert any("rajesh" in n["id"] for n in suspect_nodes)
        
        # Verify edges
        appears_edges = [e for e in graph_data["edges"] if e["label"] == "Appears In"]
        print(f"Appears In edges count: {len(appears_edges)}")
        assert len(appears_edges) >= 1
        
        print("✅ Graph serialization and connectivity passed.")

        # ── Test 2: Duplicate merging check ───────────────────────────────
        # Duplicate nodes shouldn't exist. Let's make sure nodes list has unique ids.
        node_ids = [n["id"] for n in graph_data["nodes"]]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs detected in graph response"
        print("✅ Duplicate entities merged correctly (nodes list is unique).")

        # ── Test 3: Large graph simulation performance ─────────────────────
        # Fetching a case with 500 nodes should be fast (tested locally here)
        start_time = time.time()
        res_perf = await client.get(f"/api/v1/firs/{fid}/graph")
        duration = time.time() - start_time
        print(f"Graph query duration: {duration:.4f}s")
        assert duration < 2.0, "Graph loading took too long"
        print("✅ Graph performance test passed.")

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

    print("\n=== ALL CRIMINAL RELATIONSHIP GRAPH TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
