import asyncio
from functools import lru_cache

from fastembed import TextEmbedding

from app.constants.question_bank import EMBEDDING_MODEL_NAME


@lru_cache
def get_embedding_model() -> TextEmbedding:
    """Cached local embedding model, loaded lazily like get_gemini_client()."""
    return TextEmbedding(model_name=EMBEDDING_MODEL_NAME)


def _embed_sync(text: str) -> list[float]:
    (embedding,) = get_embedding_model().embed([text])
    return embedding.tolist()


async def embed_text(text: str) -> list[float]:
    """Embeds one string for pgvector similarity search."""
    return await asyncio.to_thread(_embed_sync, text)
