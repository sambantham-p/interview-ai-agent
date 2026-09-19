import time

import httpx
import structlog
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.constants.search import (
    MAX_SEARCH_RESULT_CHARS,
    SEARCH_MCP_TIMEOUT_SECONDS,
    SEARCH_MCP_TOOL_NAME,
    SEARCH_MCP_URL,
)

logger = structlog.get_logger(__name__)


class SearchTransientError(Exception):
    """A retryable or unexpected failure connecting to / calling the
    Search MCP server. Mirrors GitHubTransientError/GeminiTransientError's role
    in their own clients: callers catch this and continue the interview without
    company research rather than letting it break a turn.
    """


async def search_company_context(*, company_name: str, role: str) -> str:
    """Runs one real MCP round-trip against Parallel's public Search MCP
    server to ground Phase 6/7 with real, current information about the company.

    Fetched once per interview (see prefetch_company_research in
    interview_service.py), never live on a per-turn basis and same
    single-prefetch reasoning as the RAG question pool.

    Raises SearchTransientError on any connection/protocol/tool failure;
    never returns a partial or fabricated result.
    """
    log = logger.bind(company_name=company_name)
    start_time = time.monotonic()
    try:
        async with (
            httpx.AsyncClient(
                timeout=SEARCH_MCP_TIMEOUT_SECONDS, follow_redirects=True
            ) as http_client,
            streamable_http_client(SEARCH_MCP_URL, http_client=http_client) as (
                read_stream,
                write_stream,
                _,
            ),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.call_tool(
                SEARCH_MCP_TOOL_NAME,
                arguments={
                    "objective": (
                        f"Recent, factual information about {company_name} as "
                        f"a company - what they do, products, and any recent "
                        f"news - relevant to a candidate interviewing for a "
                        f"{role} role there."
                    ),
                    "search_queries": [f"{company_name} company overview"],
                },
            )
    except Exception as exc:
        log.warning(
            "search_mcp.error",
            duration_seconds=time.monotonic() - start_time,
            error=str(exc),
        )
        raise SearchTransientError(str(exc)) from exc

    duration_seconds = time.monotonic() - start_time
    if result.isError:
        log.warning("search_mcp.tool_error", duration_seconds=duration_seconds)
        raise SearchTransientError(
            f"Search MCP tool reported an error for {company_name!r}"
        )

    text = "\n".join(
        block.text for block in result.content if getattr(block, "text", None)
    )
    log.info("search_mcp.success", duration_seconds=duration_seconds, chars=len(text))
    return text[:MAX_SEARCH_RESULT_CHARS]
