from app.constants.question_bank import QUESTION_EMBEDDING_DIM
from app.core.config import get_gateway_settings
from app.core.gemini_client import EmbeddingTaskType, embed_content


async def embed_text(
    text: str, task_type: EmbeddingTaskType = "RETRIEVAL_QUERY"
) -> list[float]:
    """Embeds one string for pgvector similarity search. Questions being
    stored use RETRIEVAL_DOCUMENT; the JD-derived search text uses the
    default RETRIEVAL_QUERY.
    """
    return await embed_content(
        model=get_gateway_settings().gemini_embedding_model,
        text=text,
        task_type=task_type,
        dimensions=QUESTION_EMBEDDING_DIM,
    )
