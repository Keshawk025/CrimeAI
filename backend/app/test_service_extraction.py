import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.models.fir import FIR, FileType, FIRStatus
from app.models.fir_document_content import FIRDocumentContent
from app.db.init_db import check_db_connection
from app.services.fir_service import extract_and_save_fir_text

async def run_tests():
    print("=== STARTING SERVICE EXTRACTION TEST ===")
    
    # Ensure DB connection & tables are initialized
    db_ok = await check_db_connection()
    if not db_ok:
        print("❌ Database connection check failed.")
        sys.exit(1)
    print("✅ Database connection check passed.")

    # Prepare real and corrupted test files
    temp_dir = tempfile.mkdtemp()
    
    # 1. TXT File
    txt_path = Path(temp_dir) / "test_fir.txt"
    txt_path.write_text("This is a plain text First Information Report (FIR) from Karnataka Police. The suspect was seen near Vidhana Soudha at 10:00 PM.")
    
    # 2. PDF File
    pdf_path = Path(temp_dir) / "test_fir.pdf"
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "This is a valid PDF document with text content for test cases.")
        doc.save(str(pdf_path))
        doc.close()
        print("Generated valid PDF using PyMuPDF.")
    except Exception as e:
        print(f"Could not use PyMuPDF to generate valid test PDF ({e}). Writing mock pdf.")
        pdf_path.write_text("mock pdf data")

    # 3. DOCX File
    docx_path = Path(temp_dir) / "test_fir.docx"
    try:
        import docx
        doc = docx.Document()
        doc.add_paragraph("This is a valid Word Document (DOCX) for FIR extraction testing.")
        doc.save(str(docx_path))
        print("Generated valid DOCX using python-docx.")
    except Exception as e:
        print(f"Could not use python-docx to generate valid test DOCX ({e}). Writing mock docx.")
        docx_path.write_text("mock docx data")

    # 4. Corrupted PDF File
    corrupted_pdf_path = Path(temp_dir) / "corrupted.pdf"
    corrupted_pdf_path.write_bytes(b"INVALID PDF DATA CHUNKS")

    # 5. Empty Document
    empty_txt_path = Path(temp_dir) / "empty.txt"
    empty_txt_path.write_text("")

    async with AsyncSessionLocal() as db:
        # Clean up any existing test FIRs
        from sqlalchemy import delete
        await db.execute(delete(FIRDocumentContent))
        await db.execute(delete(FIR))
        await db.commit()

        # Helper to create FIR
        async def create_fir(file_path: Path, case_num: str, file_type: FileType) -> FIR:
            fir = FIR(
                case_number=case_num,
                original_filename=file_path.name,
                file_type=file_type,
                file_size=os.path.getsize(file_path),
                storage_path=str(file_path),
                status=FIRStatus.UPLOADED,
                created_by="tester",
            )
            db.add(fir)
            await db.commit()
            await db.refresh(fir)
            return fir

        # Create records
        fir_txt = await create_fir(txt_path, "CASE-TXT-001", FileType.TXT)
        fir_pdf = await create_fir(pdf_path, "CASE-PDF-002", FileType.PDF)
        fir_docx = await create_fir(docx_path, "CASE-DOCX-003", FileType.DOCX)
        fir_empty = await create_fir(empty_txt_path, "CASE-EMPTY-004", FileType.TXT)
        fir_corr = await create_fir(corrupted_pdf_path, "CASE-CORR-005", FileType.PDF)

        # Test 1: TXT Extraction
        print("\n[Test 1] Extracting TXT Document...")
        doc_content_txt = await extract_and_save_fir_text(db, fir_txt.id)
        assert doc_content_txt.extracted_text == txt_path.read_text(), "TXT Text mismatch"
        assert doc_content_txt.word_count == len(txt_path.read_text().split())
        assert doc_content_txt.character_count == len(txt_path.read_text())
        assert doc_content_txt.extraction_status == "success"
        print(f"✅ TXT Extracted: words={doc_content_txt.word_count}, chars={doc_content_txt.character_count}, lang={doc_content_txt.language}")

        # Test 2: PDF Extraction
        print("\n[Test 2] Extracting PDF Document...")
        doc_content = await extract_and_save_fir_text(db, fir_pdf.id)
        assert "valid PDF document" in doc_content.extracted_text, "PDF Text mismatch"
        assert doc_content.page_count == 1
        assert doc_content.extraction_status == "success"
        print(f"✅ PDF Extracted: words={doc_content.word_count}, chars={doc_content.character_count}, lang={doc_content.language}")

        # Test 3: DOCX Extraction
        print("\n[Test 3] Extracting DOCX Document...")
        doc_content = await extract_and_save_fir_text(db, fir_docx.id)
        assert "valid Word Document" in doc_content.extracted_text, "DOCX Text mismatch"
        assert doc_content.page_count >= 1
        assert doc_content.extraction_status == "success"
        print(f"✅ DOCX Extracted: words={doc_content.word_count}, chars={doc_content.character_count}, lang={doc_content.language}")

        # Test 4: Empty Document
        print("\n[Test 4] Extracting Empty Document...")
        doc_content = await extract_and_save_fir_text(db, fir_empty.id)
        assert doc_content.extracted_text == "", "Empty text mismatch"
        assert doc_content.word_count == 0
        assert doc_content.character_count == 0
        print("✅ Empty Document handled successfully.")

        # Test 5: Corrupted PDF Document (should raise ValueError)
        print("\n[Test 5] Extracting Corrupted PDF...")
        try:
            await extract_and_save_fir_text(db, fir_corr.id)
            print("❌ Expected extraction of corrupted PDF to raise ValueError, but it succeeded!")
            sys.exit(1)
        except ValueError as e:
            print(f"✅ Corrupted PDF successfully raised error: {e}")

        # Test 6: Duplicate Extraction Updates Existing Record
        print("\n[Test 6] Duplicate Extraction (Update)...")
        # Trigger second extraction on fir_txt
        doc_content_dup = await extract_and_save_fir_text(db, fir_txt.id)
        assert doc_content_txt.id == doc_content_dup.id, "Expected same record ID to be updated"
        
        # Verify db contents count
        stmt = select(FIRDocumentContent)
        res_db = await db.execute(stmt)
        records = res_db.scalars().all()
        assert len(records) == 4, f"Expected exactly 4 records, got {len(records)}"
        print("✅ Duplicate extraction successfully updated existing record instead of duplicating.")

        # Cleanup test records
        print("\nCleaning up database...")
        await db.execute(delete(FIRDocumentContent))
        await db.execute(delete(FIR))
        await db.commit()

    shutil.rmtree(temp_dir)
    print("\n=== ALL SERVICE EXTRACTION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
