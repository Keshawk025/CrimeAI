"""
app/services/fir_service.py
────────────────────────────
Business logic for FIR upload and retrieval.

Responsibilities:
- Validate MIME type and file size
- Detect duplicate uploads (same hash)
- Save file to /storage/firs/
- Persist and query FIR metadata via SQLAlchemy
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.fir import FIR, FileType, FIRStatus
from app.models.fir_document_content import FIRDocumentContent
from app.schemas.fir import FIRCreate
from app.services.document_processor import extract_text

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

ALLOWED_MIME_TYPES: dict[str, FileType] = {
    "application/pdf": FileType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    "text/plain": FileType.TXT,
}

ALLOWED_EXTENSIONS: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".txt": FileType.TXT,
}

STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage" / "firs"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_file_type(filename: str, content_type: str | None) -> FileType:
    """
    Resolve FileType from the file extension first, then fall back to MIME.
    Raises ValueError if neither is acceptable.
    """
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_EXTENSIONS:
        return ALLOWED_EXTENSIONS[ext]
    if content_type and content_type in ALLOWED_MIME_TYPES:
        return ALLOWED_MIME_TYPES[content_type]
    raise ValueError(
        f"Unsupported file type: '{ext}'. Allowed: PDF, DOCX, TXT."
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Service functions ──────────────────────────────────────────────────────────

async def upload_fir(
    db: AsyncSession,
    file: UploadFile,
    case_number: str,
    created_by: str = "system",
) -> FIR:
    """
    Validate, store, and persist a single FIR document.

    Parameters
    ----------
    db:         Active async DB session.
    file:       The uploaded file from FastAPI.
    case_number: Investigator-supplied case identifier.
    created_by: Username or system tag.

    Raises
    ------
    ValueError
        On type/size/duplicate violations.
    """
    # ── 1. Read file into memory ───────────────────────────────
    content = await file.read()
    file_size = len(content)

    # ── 2. Size validation ─────────────────────────────────────
    if file_size == 0:
        raise ValueError("Uploaded file is empty.")
    if file_size > MAX_FILE_SIZE:
        raise ValueError(
            f"File size {file_size / (1024*1024):.1f} MB exceeds the 20 MB limit."
        )

    # ── 3. Type validation ─────────────────────────────────────
    filename = file.filename or "upload"
    file_type = _resolve_file_type(filename, file.content_type)

    # ── 4. Duplicate detection (SHA-256 content hash) ──────────
    content_hash = _sha256(content)
    dup_path_fragment = content_hash  # used in storage_path

    existing = await db.execute(
        select(FIR).where(FIR.storage_path.contains(content_hash[:12]))
    )
    if existing.scalar_one_or_none():
        raise ValueError(
            "Duplicate upload detected — this file has already been stored."
        )

    # ── 5. Persist to disk ─────────────────────────────────────
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    unique_name = f"{content_hash[:12]}_{uuid.uuid4().hex[:8]}{Path(filename).suffix.lower()}"
    dest_path = STORAGE_ROOT / unique_name

    dest_path.write_bytes(content)
    logger.info(
        "[FIR] Saved file: %s (%d bytes)", dest_path.name, file_size
    )

    # ── 6. Persist metadata ────────────────────────────────────
    fir = FIR(
        case_number=case_number,
        original_filename=filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=str(dest_path),
        status=FIRStatus.UPLOADED,
        created_by=created_by,
    )
    db.add(fir)
    await db.commit()
    await db.refresh(fir)

    logger.info(
        "[FIR] Metadata saved — id=%s case=%s", fir.id, fir.case_number
    )
    return fir


async def list_firs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> tuple[int, list[FIR]]:
    """Return (total_count, paginated_list) of all FIRs ordered by upload time."""
    from sqlalchemy import func as sa_func

    total_result = await db.execute(
        select(sa_func.count()).select_from(FIR)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(FIR).order_by(FIR.uploaded_at.desc()).offset(skip).limit(limit)
    )
    return total, list(result.scalars().all())


async def get_fir(db: AsyncSession, fir_id: uuid.UUID) -> FIR | None:
    """Fetch a single FIR by its UUID, or return None."""
    result = await db.execute(select(FIR).where(FIR.id == fir_id))
    return result.scalar_one_or_none()


async def delete_fir(db: AsyncSession, fir_id: uuid.UUID) -> FIR | None:
    """
    Delete a FIR record and its associated file from disk.
    Returns the deleted FIR record or None if not found.
    """
    fir = await get_fir(db, fir_id)
    if fir is None:
        return None

    # Remove file from disk
    file_path = Path(fir.storage_path)
    if file_path.exists():
        file_path.unlink()
        logger.info("[FIR] Deleted file: %s", file_path.name)

    # Delete from Qdrant if indexed
    try:
        from app.services.qdrant_index_service import QdrantIndexService
        qdrant_index_service = QdrantIndexService()
        await qdrant_index_service.delete_vector(fir_id)
    except Exception as exc:
        logger.warning("[FIR] Failed to delete Qdrant vector for deleted FIR: %s", exc)

    await db.delete(fir)
    await db.commit()
    logger.info("[FIR] Record deleted — id=%s", fir_id)
    return fir


async def extract_and_save_fir_text(db: AsyncSession, fir_id: uuid.UUID) -> FIRDocumentContent:
    """
    Find FIR, verify file, extract text, calculate statistics, and save/update the FIRDocumentContent.
    """
    fir = await get_fir(db, fir_id)
    if fir is None:
        raise ValueError(f"FIR with id '{fir_id}' not found.")

    file_path = Path(fir.storage_path)
    if not file_path.exists():
        raise FileNotFoundError(f"FIR file not found on disk at: {fir.storage_path}")

    # Perform extraction
    try:
        extraction = extract_text(str(file_path))
    except Exception as e:
        logger.error(f"Text extraction failed for FIR {fir_id}: {e}")
        raise ValueError(f"Document extraction failed: {str(e)}")

    # Check if a content record already exists
    existing_result = await db.execute(
        select(FIRDocumentContent).where(FIRDocumentContent.fir_id == fir_id)
    )
    doc_content = existing_result.scalar_one_or_none()

    from datetime import datetime, timezone

    if doc_content:
        # Update existing record
        doc_content.extracted_text = extraction["text"]
        doc_content.page_count = extraction["page_count"]
        doc_content.word_count = extraction["word_count"]
        doc_content.character_count = extraction["character_count"]
        doc_content.language = extraction["language"]
        doc_content.extraction_status = "success"
        doc_content.extracted_at = datetime.now(timezone.utc)
    else:
        # Create new record
        doc_content = FIRDocumentContent(
            fir_id=fir_id,
            extracted_text=extraction["text"],
            page_count=extraction["page_count"],
            word_count=extraction["word_count"],
            character_count=extraction["character_count"],
            language=extraction["language"],
            extraction_status="success",
            extracted_at=datetime.now(timezone.utc),
        )
        db.add(doc_content)

    fir.status = FIRStatus.TEXT_EXTRACTED
    await db.commit()
    await db.refresh(doc_content)
    logger.info(f"[FIR] Extracted text saved/updated for FIR id={fir_id}")
    return doc_content
