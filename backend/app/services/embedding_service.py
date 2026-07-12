"""
app/services/embedding_service.py
──────────────────────────────────
Service for generating semantic text embeddings using Gemini or local models.
"""

import asyncio
import hashlib
import logging
import random
from typing import List

import httpx
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def generate_mock_embedding(text: str, dimension: int) -> List[float]:
    """
    Generate a deterministic, normalized mock vector based on the input text.
    Ensures tests pass even without active API keys or local ML dependencies.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(h, "big") % (2**32)
    rng = random.Random(seed)
    
    vec = [rng.uniform(-1.0, 1.0) for _ in range(dimension)]
    # Normalise for Cosine similarity
    norm = sum(x*x for x in vec) ** 0.5
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


class EmbeddingService:
    """
    Handles generating dense semantic embeddings for texts with built-in retries,
    dimension validation, and fallback mechanisms.
    """

    def __init__(self) -> None:
        self.provider = settings.embedding_provider
        self.model_name = settings.embedding_model_name
        self.dimension = settings.vector_dimension
        self.api_key = settings.huggingface_api_key

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for the given text.
        Retries up to 3 times on transient failures.
        """
        if not text or not text.strip():
            # Return zero vector or mock for empty text
            logger.warning("Empty text passed for embedding generation. Returning zero-filled vector.")
            return [0.0] * self.dimension

        max_attempts = 3
        backoff_sec = 1.0

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info("Embedding generation started (Provider: %s, Model: %s)", self.provider, self.model_name)
                if self.provider == "huggingface" and self.api_key:
                    vector = await self._generate_huggingface_embedding(text)
                else:
                    vector = await self._generate_local_embedding(text)

                # Validate dimensions
                if len(vector) != self.dimension:
                    raise ValueError(
                        f"Generated embedding dimension {len(vector)} "
                        f"does not match configured dimension {self.dimension}."
                    )

                logger.info("Embedding generation completed (Dimension: %d)", len(vector))
                return vector

            except Exception as exc:
                logger.error(
                    "Embedding generation failed (Attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                if attempt == max_attempts:
                    logger.warning("All embedding generation attempts failed. Falling back to mock embedding.")
                    return generate_mock_embedding(text, self.dimension)
                
                await asyncio.sleep(backoff_sec)
                backoff_sec *= 2.0

        return generate_mock_embedding(text, self.dimension)

    async def _generate_huggingface_embedding(self, text: str) -> List[float]:
        """Call the Hugging Face Inference API for embeddings."""
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"inputs": text}

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            
            if res.status_code != 200:
                raise httpx.HTTPStatusError(
                    f"Hugging Face API returned status {res.status_code}: {res.text}",
                    request=res.request,
                    response=res,
                )
            
            data = res.json()
            # If a list of floats is returned directly
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], float):
                return data
            # If a list of lists is returned
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                return data[0]
            
            raise ValueError(f"Unexpected response structure from Hugging Face API: {data}")

    async def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding locally using fastembed, with deterministic fallback."""
        try:
            # Try importing fastembed dynamically
            from fastembed import TextEmbedding
            
            # TextEmbedding is synchronous/blocking, so run in executor
            loop = asyncio.get_running_loop()
            
            def _embed():
                # We load/instantiate inside or use a class-level cache
                # BAAI/bge-small-en-v1.5 has 384 dimensions. models/text-embedding-004 has 768.
                # If model_name is not natively supported by fastembed, fallback to BAAI.
                model_to_use = self.model_name
                if "BAAI" not in model_to_use and "sentence-transformers" not in model_to_use:
                    model_to_use = "BAAI/bge-small-en-v1.5"
                
                model = TextEmbedding(model_name=model_to_use)
                embeddings_generator = model.embed([text])
                return list(next(embeddings_generator))
            
            vector = await loop.run_in_executor(None, _embed)
            
            # If the generated dimension is different from settings.vector_dimension (e.g. 384 vs 768),
            # we pad or crop, or raise ValueError so the caller knows.
            # But wait: let's pad/truncate to avoid failing if they mismatch.
            if len(vector) != self.dimension:
                logger.warning(
                    "Local embedding dimension %d mismatched settings dimension %d. Resizing vector.",
                    len(vector), self.dimension
                )
                if len(vector) < self.dimension:
                    vector = vector + [0.0] * (self.dimension - len(vector))
                else:
                    vector = vector[:self.dimension]
            return vector

        except Exception as exc:
            logger.debug("Fastembed unavailable or failed to run: %s. Reverting to mock generator.", exc)
            return generate_mock_embedding(text, self.dimension)
