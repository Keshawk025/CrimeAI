"""
app/api/v1/firs.py
───────────────────
FIR upload and document management API.

Endpoints:
    POST   /api/firs/upload     — upload a new FIR document
    GET    /api/firs            — list all uploaded FIRs
    GET    /api/firs/{id}       — retrieve a single FIR
    DELETE /api/firs/{id}       — delete a FIR and its file
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.schemas.fir import (
    FIRDeleteResponse,
    FIRListResponse,
    FIRRead,
    FIRUploadResponse,
)
from app.schemas.fir_document_content import FIRDocumentContentRead
from app.schemas.fir_entity import FIREntityRead
from app.services.fir_service import (
    delete_fir,
    get_fir,
    list_firs,
    upload_fir,
    extract_and_save_fir_text,
)
from app.services.entity_extraction_service import extract_and_save_entities

# Embedding imports
from datetime import datetime
from sqlalchemy import select, func
from app.schemas.fir_embedding import FIREmbeddingRead
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_index_service import QdrantIndexService
from app.models.fir import FIR, FIRStatus
from app.models.fir_embedding import FIREmbedding
from app.models.fir_document_content import FIRDocumentContent
from app.models.fir_entity import FIREntity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/firs", tags=["FIRs"])


# ── DB dependency ──────────────────────────────────────────────────────────────

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=FIRUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a FIR document",
    description=(
        "Upload a First Information Report (FIR) document. "
        "Accepted formats: PDF, DOCX, TXT. Maximum size: 20 MB."
    ),
)
async def upload_fir_endpoint(
    file: UploadFile = File(..., description="FIR document (PDF, DOCX, or TXT)"),
    case_number: str = Form(..., min_length=1, max_length=100, description="Unique case number"),
    created_by: str = Form(default="system", max_length=255),
    db: AsyncSession = Depends(get_db),
) -> FIRUploadResponse:
    logger.info(
        "[POST /firs/upload] case=%s file=%s size=%s type=%s",
        case_number,
        file.filename,
        file.size,
        file.content_type,
    )

    try:
        fir = await upload_fir(db, file, case_number, created_by)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("[POST /firs/upload] Unexpected error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing upload.",
        )

    return FIRUploadResponse(
        id=fir.id,
        case_number=fir.case_number,
        original_filename=fir.original_filename,
        file_type=fir.file_type,
        file_size=fir.file_size,
        status=fir.status,
        uploaded_at=fir.uploaded_at,
    )


# ── List ───────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=FIRListResponse,
    summary="List all uploaded FIRs",
)
async def list_firs_endpoint(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> FIRListResponse:
    total, firs = await list_firs(db, skip=skip, limit=limit)
    return FIRListResponse(total=total, items=firs)


# ── Get by ID ──────────────────────────────────────────────────────────────────

@router.get(
    "/{fir_id}",
    response_model=FIRRead,
    summary="Get a single FIR by ID",
)
async def get_fir_endpoint(
    fir_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FIRRead:
    fir = await get_fir(db, fir_id)
    if fir is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FIR with id '{fir_id}' not found.",
        )
    return FIRRead.model_validate(fir)


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.delete(
    "/{fir_id}",
    response_model=FIRDeleteResponse,
    summary="Delete a FIR document",
)
async def delete_fir_endpoint(
    fir_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FIRDeleteResponse:
    fir = await delete_fir(db, fir_id)
    if fir is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FIR with id '{fir_id}' not found.",
        )
    return FIRDeleteResponse(id=fir_id)


@router.post(
    "/{fir_id}/extract",
    response_model=FIRDocumentContentRead,
    status_code=status.HTTP_200_OK,
    summary="Extract text and metadata from a FIR document",
)
async def extract_fir_text_endpoint(
    fir_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FIRDocumentContentRead:
    logger.info("[POST /firs/%s/extract] Triggering text extraction", fir_id)
    try:
        doc_content = await extract_and_save_fir_text(db, fir_id)
        return doc_content
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("[POST /firs/%s/extract] Unexpected error: %s", fir_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during text extraction: {exc}",
        )


@router.post(
    "/{fir_id}/entities",
    response_model=list[FIREntityRead],
    status_code=status.HTTP_200_OK,
    summary="Extract structured entities from a FIR document using Gemini",
)
async def extract_fir_entities_endpoint(
    fir_id: uuid.UUID,
    force_invalid_once: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[FIREntityRead]:
    logger.info("[POST /firs/%s/entities] Triggering entity extraction", fir_id)
    try:
        entities = await extract_and_save_entities(db, fir_id, force_invalid_once=force_invalid_once)
        return entities
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("[POST /firs/%s/entities] Unexpected error: %s", fir_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during entity extraction: {exc}",
        )


@router.post(
    "/{fir_id}/index",
    response_model=FIREmbeddingRead,
    status_code=status.HTTP_200_OK,
    summary="Generate embeddings and index the FIR document in Qdrant",
)
async def index_fir_document_endpoint(
    fir_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FIREmbeddingRead:
    logger.info("[POST /firs/%s/index] Starting indexing process", fir_id)
    
    # 1. Fetch FIR record from database
    fir = await get_fir(db, fir_id)
    if fir is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FIR with id '{fir_id}' not found.",
        )
        
    # 2. Retrieve extracted text
    doc_content_stmt = select(FIRDocumentContent).where(FIRDocumentContent.fir_id == fir_id)
    doc_content_res = await db.execute(doc_content_stmt)
    doc_content = doc_content_res.scalar_one_or_none()
    
    if doc_content is None or not doc_content.extracted_text or not doc_content.extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FIR text content has not been extracted yet. Please extract text first.",
        )
        
    # 3. Retrieve entities for the payload summary
    entities_stmt = select(FIREntity).where(FIREntity.fir_id == fir_id)
    entities_res = await db.execute(entities_stmt)
    entities = entities_res.scalars().all()
    
    # Build entity_summary and crime_type
    crime_type = "Unknown"
    summary_parts = []
    grouped_entities = {}
    for ent in entities:
        t = ent.entity_type
        val = ent.entity_value
        if t == "crime_category":
            crime_type = val
        if t not in grouped_entities:
            grouped_entities[t] = []
        grouped_entities[t].append(val)

    for t, vals in grouped_entities.items():
        label = t.capitalize() + "s"
        summary_parts.append(f"{label}: {', '.join(vals)}")

    entity_summary = "; ".join(summary_parts) if summary_parts else "No entities extracted"
    
    # Build payload
    payload = {
        "fir_id": str(fir_id),
        "case_number": fir.case_number,
        "crime_type": crime_type,
        "upload_date": fir.uploaded_at.isoformat() if fir.uploaded_at else datetime.utcnow().isoformat(),
        "extracted_text_preview": doc_content.extracted_text[:1000],
        "entity_summary": entity_summary,
    }
    
    # 4. Generate Embedding
    embedding_service = EmbeddingService()
    try:
        vector = await embedding_service.generate_embedding(doc_content.extracted_text)
    except Exception as exc:
        logger.exception("Failed to generate embedding: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embedding: {exc}",
        )
        
    # 5. Store vector in Qdrant
    qdrant_index_service = QdrantIndexService()
    point_id = await qdrant_index_service.upsert_vector(fir_id, vector, payload)
    
    # 6. Save metadata in PostgreSQL (table fir_embeddings)
    stmt_embedding = select(FIREmbedding).where(FIREmbedding.fir_id == fir_id)
    res_embedding = await db.execute(stmt_embedding)
    existing_embedding = res_embedding.scalar_one_or_none()
    
    if existing_embedding:
        existing_embedding.qdrant_point_id = point_id
        existing_embedding.embedding_model = embedding_service.model_name
        existing_embedding.vector_dimension = embedding_service.dimension
        existing_embedding.indexed_at = func.now()
        db_embedding = existing_embedding
    else:
        db_embedding = FIREmbedding(
            fir_id=fir_id,
            qdrant_point_id=point_id,
            embedding_model=embedding_service.model_name,
            vector_dimension=embedding_service.dimension,
        )
        db.add(db_embedding)
        
    try:
        if entities:
            fir.status = FIRStatus.READY_FOR_INVESTIGATION
        else:
            fir.status = FIRStatus.INDEXED
        await db.commit()
        await db.refresh(db_embedding)
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to write embedding metadata to database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database commit failed: {exc}",
        )
        
    return db_embedding
