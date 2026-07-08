"""
app/services/qdrant_service.py
───────────────────────────────
Production-ready Qdrant integration layer.

Responsibilities
----------------
* Manage a single shared async QdrantClient instance.
* Bootstrap the target collection on startup (create if absent).
* Expose reusable CRUD stubs for document vectors:
    - create_collection()
    - collection_exists()
    - upsert_document()
    - search_similar()
    - delete_document()

Business / embedding logic is intentionally deferred to future tasks.
"""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config.settings import get_settings
from app.core.exceptions import ServiceUnavailableException

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Singleton client ───────────────────────────────────────────────────────────

_qdrant_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    """
    Return the module-level async Qdrant client.
    Call :func:`init_qdrant_client` during application startup first.
    """
    if _qdrant_client is None:
        raise ServiceUnavailableException(
            "Qdrant client has not been initialised. "
            "Ensure init_qdrant_client() is called during startup."
        )
    return _qdrant_client


async def init_qdrant_client() -> AsyncQdrantClient:
    """
    Create the async Qdrant client and store it as a module singleton.
    Should be called once inside the FastAPI lifespan startup hook.
    """
    global _qdrant_client

    kwargs: dict[str, Any] = {
        "url": settings.qdrant_url,
        "check_compatibility": False,   # suppress version-mismatch warnings on startup
    }
    if settings.qdrant_api_key:
        kwargs["api_key"] = settings.qdrant_api_key

    logger.info("Initialising Qdrant client → %s", settings.qdrant_url)
    _qdrant_client = AsyncQdrantClient(**kwargs)
    return _qdrant_client


async def close_qdrant_client() -> None:
    """Gracefully close the async client. Call during shutdown."""
    global _qdrant_client
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
        logger.info("Qdrant client closed.")


# ── QdrantService ──────────────────────────────────────────────────────────────


class QdrantService:
    """
    High-level service wrapping :class:`AsyncQdrantClient`.

    All methods are async and accept an optional *client* argument so they
    can be used both as FastAPI dependencies and in standalone scripts.
    """

    def __init__(self, client: AsyncQdrantClient | None = None) -> None:
        self._client = client or get_qdrant_client()
        self._collection = settings.qdrant_collection
        self._vector_size = settings.vector_dimension

    # ── Collection management ──────────────────────────────────

    async def collection_exists(self) -> bool:
        """
        Return *True* if the configured collection already exists in Qdrant.

        Raises
        ------
        ServiceUnavailableException
            If Qdrant is unreachable.
        """
        try:
            return await self._client.collection_exists(self._collection)
        except Exception as exc:
            logger.error(
                "Failed to check Qdrant collection existence [%s]: %s",
                self._collection,
                exc,
            )
            raise ServiceUnavailableException(
                f"Qdrant is unavailable: {exc}"
            ) from exc

    async def create_collection(self) -> bool:
        """
        Create the collection with Cosine distance and the configured vector
        dimension.  No-ops if the collection already exists.

        Returns
        -------
        bool
            *True* if a new collection was created, *False* if it already existed.
        """
        if await self.collection_exists():
            logger.info(
                "Qdrant collection '%s' already exists — skipping creation.",
                self._collection,
            )
            return False

        try:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qdrant_models.VectorParams(
                    size=self._vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(
                "Qdrant collection '%s' created (dim=%d, metric=Cosine).",
                self._collection,
                self._vector_size,
            )
            return True
        except UnexpectedResponse as exc:
            logger.error(
                "Unexpected Qdrant response while creating collection '%s': %s",
                self._collection,
                exc,
            )
            raise ServiceUnavailableException(
                f"Could not create Qdrant collection: {exc}"
            ) from exc
        except Exception as exc:
            logger.error("Error creating Qdrant collection: %s", exc)
            raise ServiceUnavailableException(str(exc)) from exc

    # ── Document operations ────────────────────────────────────

    async def upsert_document(
        self,
        doc_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """
        Insert or update a single document vector in Qdrant.

        Parameters
        ----------
        doc_id:
            Unique string identifier for the document (converted to a
            deterministic UUID internally via Qdrant's string-ID support).
        vector:
            Dense embedding of length ``settings.vector_dimension``.
        payload:
            Arbitrary JSON-serialisable metadata stored alongside the vector
            (e.g. FIR number, file path, chunk index).

        .. note::
            Embedding generation is **not** the responsibility of this method.
            The caller must supply a pre-computed vector.
        """
        try:
            await self._client.upsert(
                collection_name=self._collection,
                points=[
                    qdrant_models.PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )
            logger.debug("Upserted document id=%s into '%s'.", doc_id, self._collection)
        except Exception as exc:
            logger.error("Failed to upsert document id=%s: %s", doc_id, exc)
            raise ServiceUnavailableException(f"Qdrant upsert failed: {exc}") from exc

    async def search_similar(
        self,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        filters: qdrant_models.Filter | None = None,
    ) -> list[qdrant_models.ScoredPoint]:
        """
        Perform a cosine-similarity nearest-neighbour search.

        Parameters
        ----------
        query_vector:
            Dense embedding of length ``settings.vector_dimension``.
        top_k:
            Maximum number of results to return.
        score_threshold:
            Minimum similarity score (0–1) to include in results.
        filters:
            Optional Qdrant :class:`~qdrant_client.http.models.Filter` to
            narrow the search to a subset of documents.

        Returns
        -------
        list[ScoredPoint]
            Ranked list of matching points with scores and payloads.

        .. note::
            Query embedding generation is **not** the responsibility of this
            method. The caller must supply a pre-computed vector.
        """
        try:
            response = await self._client.query_points(
                collection_name=self._collection,
                query=query_vector,
                limit=top_k,
                score_threshold=score_threshold if score_threshold > 0 else None,
                query_filter=filters,
                with_payload=True,
            )
            results = response.points
            logger.debug(
                "search_similar returned %d results (top_k=%d).", len(results), top_k
            )
            return results
        except Exception as exc:
            logger.error("Qdrant search failed: %s", exc)
            raise ServiceUnavailableException(f"Qdrant search failed: {exc}") from exc

    async def delete_document(self, doc_id: str) -> None:
        """
        Delete a single document vector by its ID.

        Parameters
        ----------
        doc_id:
            The string ID that was used when upserting the document.
        """
        try:
            await self._client.delete(
                collection_name=self._collection,
                points_selector=qdrant_models.PointIdsList(points=[doc_id]),
            )
            logger.debug(
                "Deleted document id=%s from '%s'.", doc_id, self._collection
            )
        except Exception as exc:
            logger.error("Failed to delete document id=%s: %s", doc_id, exc)
            raise ServiceUnavailableException(
                f"Qdrant delete failed: {exc}"
            ) from exc


# ── Module-level convenience instance ─────────────────────────────────────────

def get_qdrant_service() -> QdrantService:
    """
    FastAPI dependency that returns a :class:`QdrantService` backed by the
    module-level singleton client.

    Usage::

        @router.get("/example")
        async def example(qdrant: QdrantService = Depends(get_qdrant_service)):
            ...
    """
    return QdrantService(client=get_qdrant_client())
