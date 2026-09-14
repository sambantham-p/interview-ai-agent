from contextlib import asynccontextmanager

import pytest
from pytest_mock import MockerFixture

from app.constants.search import MAX_SEARCH_RESULT_CHARS
from app.core.search_mcp_client import SearchTransientError, search_company_context


@asynccontextmanager
async def _fake_streams_cm(*_args, **_kwargs):
    yield ("read_stream", "write_stream", lambda: None)


def _mock_session(
    mocker: MockerFixture, *, call_tool_result=None, call_tool_side_effect=None
):
    session = mocker.AsyncMock()
    session.initialize = mocker.AsyncMock()
    if call_tool_side_effect is not None:
        session.call_tool = mocker.AsyncMock(side_effect=call_tool_side_effect)
    else:
        session.call_tool = mocker.AsyncMock(return_value=call_tool_result)
    session.__aenter__ = mocker.AsyncMock(return_value=session)
    session.__aexit__ = mocker.AsyncMock(return_value=False)
    return session


def _mock_transport(mocker: MockerFixture, *, session):
    mocker.patch("app.core.search_mcp_client.streamable_http_client", _fake_streams_cm)
    mocker.patch("app.core.search_mcp_client.ClientSession", return_value=session)


def _fake_result(*, is_error: bool, text: str = ""):
    block = type("Block", (), {"text": text})()
    result = type(
        "Result", (), {"isError": is_error, "content": [block] if text else []}
    )()
    return result


async def test_search_company_context_returns_tool_result_text(
    mocker: MockerFixture,
) -> None:
    session = _mock_session(
        mocker,
        call_tool_result=_fake_result(is_error=False, text="Acme makes widgets."),
    )
    _mock_transport(mocker, session=session)

    result = await search_company_context(company_name="Acme Corp", role="Engineer")

    assert result == "Acme makes widgets."
    session.initialize.assert_awaited_once()
    session.call_tool.assert_awaited_once()
    assert session.call_tool.call_args.args[0] == "web_search"


async def test_search_company_context_truncates_long_results(
    mocker: MockerFixture,
) -> None:
    long_text = "x" * (MAX_SEARCH_RESULT_CHARS + 500)
    session = _mock_session(
        mocker, call_tool_result=_fake_result(is_error=False, text=long_text)
    )
    _mock_transport(mocker, session=session)

    result = await search_company_context(company_name="Acme Corp", role="Engineer")

    assert len(result) == MAX_SEARCH_RESULT_CHARS


async def test_search_company_context_raises_transient_error_on_tool_error(
    mocker: MockerFixture,
) -> None:
    session = _mock_session(mocker, call_tool_result=_fake_result(is_error=True))
    _mock_transport(mocker, session=session)

    with pytest.raises(SearchTransientError):
        await search_company_context(company_name="Acme Corp", role="Engineer")


async def test_search_company_context_raises_transient_error_on_connection_failure(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.core.search_mcp_client.streamable_http_client",
        mocker.MagicMock(side_effect=ConnectionError("boom")),
    )

    with pytest.raises(SearchTransientError):
        await search_company_context(company_name="Acme Corp", role="Engineer")
