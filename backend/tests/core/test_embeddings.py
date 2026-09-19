from pytest_mock import MockerFixture

from app.constants.question_bank import QUESTION_EMBEDDING_DIM
from app.core.embeddings import embed_text


async def test_embed_text_uses_the_configured_model_and_column_dimension(
    mocker: MockerFixture,
) -> None:
    fake_embed = mocker.patch(
        "app.core.embeddings.embed_content",
        new_callable=mocker.AsyncMock,
        return_value=[0.1, 0.2],
    )

    result = await embed_text("What is database normalization?")

    assert result == [0.1, 0.2]
    fake_embed.assert_awaited_once_with(
        model="gemini-embedding-001",
        text="What is database normalization?",
        task_type="RETRIEVAL_QUERY",
        dimensions=QUESTION_EMBEDDING_DIM,
    )


async def test_embed_text_passes_through_the_document_task_type(
    mocker: MockerFixture,
) -> None:
    fake_embed = mocker.patch(
        "app.core.embeddings.embed_content",
        new_callable=mocker.AsyncMock,
        return_value=[1.0],
    )

    await embed_text("a stored question", task_type="RETRIEVAL_DOCUMENT")

    assert fake_embed.await_args.kwargs["task_type"] == "RETRIEVAL_DOCUMENT"
