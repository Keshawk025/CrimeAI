"""
app/services/qdrant_index_service.py
─────────────────────────────────────
Service for managing the Qdrant index for FIR document embeddings.
"""

import logging
from typing import Any, Dict, List, Optional
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config.settings import get_settings
from app.core.exceptions import ServiceUnavailableException
from app.services.qdrant_service import get_qdrant_client

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_NAME = "crime_fir_embeddings"


class QdrantIndexService:
    """
    Manages vector operations inside the 'crime_fir_embeddings' collection.
    """

    def __init__(self, client: Optional[AsyncQdrantClient] = None) -> None:
        self._client = client

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is not None:
            return self._client
        return get_qdrant_client()

    async def ensure_collection_exists(self) -> None:
        """
        Check if the 'crime_fir_embeddings' collection exists, and create it if not.
        """
        try:
            exists = await self.client.collection_exists(COLLECTION_NAME)
            if not exists:
                logger.info("Creating Qdrant collection '%s'...", COLLECTION_NAME)
                await self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=qdrant_models.VectorParams(
                        size=settings.vector_dimension,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
                logger.info("Qdrant collection '%s' created successfully.", COLLECTION_NAME)
            else:
                logger.debug("Qdrant collection '%s' already exists.", COLLECTION_NAME)
        except Exception as exc:
            logger.error("Failed to ensure Qdrant collection '%s' exists: %s", COLLECTION_NAME, exc)
            raise ServiceUnavailableException(f"Qdrant collection check/creation failed: {exc}") from exc

    async def upsert_vector(
        self,
        fir_id: uuid.UUID | str,
        vector: List[float],
        payload: Dict[str, Any],
    ) -> str:
        """
        Upsert a vector along with metadata payload into Qdrant.
        Uses the FIR ID as the point ID directly.
        """
        await self.ensure_collection_exists()

        # Normalize point ID to a valid UUID string
        point_id = str(fir_id)

        try:
            await self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    qdrant_models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )
            logger.info("Upserted point id=%s in Qdrant collection '%s'.", point_id, COLLECTION_NAME)
            return point_id
        except Exception as exc:
            logger.error("Qdrant upsert failed for point %s: %s", point_id, exc)
            raise ServiceUnavailableException(f"Qdrant upsert failed: {exc}") from exc

    async def delete_vector(self, fir_id: uuid.UUID | str) -> None:
        """
        Delete the vector for a given FIR ID from Qdrant.
        """
        point_id = str(fir_id)
        try:
            # Check if collection exists first to avoid crashing
            exists = await self.client.collection_exists(COLLECTION_NAME)
            if not exists:
                return

            await self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=qdrant_models.PointIdsList(points=[point_id]),
            )
            logger.info("Deleted point id=%s from Qdrant collection '%s'.", point_id, COLLECTION_NAME)
        except Exception as exc:
            logger.error("Qdrant delete failed for point %s: %s", point_id, exc)
            raise ServiceUnavailableException(f"Qdrant delete failed: {exc}") from exc

    async def get_vector_metadata(self, fir_id: uuid.UUID | str) -> Optional[Dict[str, Any]]:
        """
        Retrieve vector payload metadata from Qdrant.
        """
        point_id = str(fir_id)
        try:
            # Check if collection exists first
            exists = await self.client.collection_exists(COLLECTION_NAME)
            if not exists:
                return None

            points = await self.client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=[point_id],
                with_payload=True,
                with_vectors=False,
            )
            if points and len(points) > 0:
                return points[0].payload
            return None
        except Exception as exc:
            logger.error("Qdrant retrieve failed for point %s: %s", point_id, exc)
            raise ServiceUnavailableException(f"Qdrant retrieve failed: {exc}") from exc
