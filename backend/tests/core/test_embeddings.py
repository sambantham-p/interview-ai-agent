from collections.abc import Iterator

import numpy as np
import pytest
from pytest_mock import MockerFixture

from app.constants.question_bank import EMBEDDING_MODEL_NAME
from app.core.embeddings import embed_text, get_embedding_model


@pytest.fixture(autouse=True)
def _clear_model_cache() -> Iterator[None]:
    get_embedding_model.cache_clear()
    yield
    get_embedding_model.cache_clear()


def test_get_embedding_model_uses_the_configured_model_name(
    mocker: MockerFixture,
) -> None:
    fake_text_embedding_cls = mocker.patch("app.core.embeddings.TextEmbedding")

    get_embedding_model()

    fake_text_embedding_cls.assert_called_once_with(model_name=EMBEDDING_MODEL_NAME)


def test_get_embedding_model_is_cached(mocker: MockerFixture) -> None:
    mocker.patch("app.core.embeddings.TextEmbedding")

    assert get_embedding_model() is get_embedding_model()


async def test_embed_text_returns_a_plain_list_of_floats(
    mocker: MockerFixture,
) -> None:
    fake_model = mocker.MagicMock()
    fake_model.embed.return_value = iter([np.array([0.1, 0.2, 0.3])])
    mocker.patch("app.core.embeddings.get_embedding_model", return_value=fake_model)

    result = await embed_text("What is database normalization?")

    assert result == [0.1, 0.2, 0.3]
    assert isinstance(result, list)
    fake_model.embed.assert_called_once_with(["What is database normalization?"])


async def test_embed_text_runs_off_the_event_loop(mocker: MockerFixture) -> None:
    fake_model = mocker.MagicMock()
    fake_model.embed.return_value = iter([np.array([1.0])])
    mocker.patch("app.core.embeddings.get_embedding_model", return_value=fake_model)
    fake_to_thread = mocker.patch(
        "app.core.embeddings.asyncio.to_thread",
        new_callable=mocker.AsyncMock,
        return_value=[1.0],
    )

    await embed_text("hello")

    fake_to_thread.assert_awaited_once()
