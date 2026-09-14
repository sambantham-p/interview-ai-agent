import base64
import time
from functools import lru_cache
from urllib.parse import urlparse

import httpx
import structlog

from app.constants.github import (
    GITHUB_API_BASE_URL,
    GITHUB_CLIENT_TIMEOUT_SECONDS,
    GITHUB_RATE_LIMIT_STATUS_CODE,
)

logger = structlog.get_logger(__name__)


class GitHubTransientError(Exception):
    """A retryable GitHub-side failure (network error, 5xx, rate-limited)
    - not the caller's fault. Mirrors GeminiTransientError/
    ElevenLabsTransientError's role in their own clients.
    """


class GitHubNotFoundError(Exception):
    """404 from GitHub's API - a real, informative tool result the model
    should see and reason about (e.g. "that file doesn't exist in this
    repo"), not a Python exception swallowed before it reaches the model.
    """


def extract_github_username(github_url: str | None) -> str | None:
    """Pulls the username out of a profile URL like
    "https://github.com/octocat" or "https://github.com/octocat/". Returns
    None for a missing/blank URL or anything not shaped like a github.com
    profile URL - callers skip tool-calling entirely in that case rather
    than guessing.
    """
    if not github_url:
        return None
    parsed = urlparse(github_url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        return None
    return segments[0]


def parse_github_repo_url(repo_url: str | None) -> tuple[str, str] | None:
    """Pulls (owner, repo) out of a repo URL like
    "https://github.com/octocat/hello-world" (with or without a trailing
    slash or ".git" suffix). Returns None for a missing/blank URL, a bare
    profile URL with no repo segment, or anything not shaped like a
    github.com repo URL - callers fall back to list_repos() + name
    matching in that case rather than guessing.
    """
    if not repo_url:
        return None
    parsed = urlparse(repo_url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1]
    return owner, repo.removesuffix(".git")


@lru_cache
def get_github_client() -> httpx.AsyncClient:
    """Return a cached, lazily created GitHub HTTP client.

    Uses GitHub's REST API directly via httpx; no SDK or authentication
    token is used. Candidates are expected to discuss public repositories,
    so unauthenticated access is intentional.
    """
    return httpx.AsyncClient(
        base_url=GITHUB_API_BASE_URL,
        headers={"Accept": "application/vnd.github+json"},
        timeout=GITHUB_CLIENT_TIMEOUT_SECONDS,
    )


async def _get_json(path: str):
    client = get_github_client()
    log = logger.bind(path=path)
    start_time = time.monotonic()
    log.info("github.request.start")

    try:
        response = await client.get(path)
    except httpx.HTTPError as exc:
        log.exception(
            "github.request.error", duration_seconds=time.monotonic() - start_time
        )
        raise GitHubTransientError(str(exc)) from exc

    duration_seconds = time.monotonic() - start_time

    if response.status_code == httpx.codes.NOT_FOUND:
        log.warning("github.request.not_found", duration_seconds=duration_seconds)
        raise GitHubNotFoundError(f"GitHub returned 404 for {path}")

    if (
        response.status_code == GITHUB_RATE_LIMIT_STATUS_CODE
        or response.status_code >= httpx.codes.INTERNAL_SERVER_ERROR
    ):
        log.warning(
            "github.request.transient_error",
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )
        raise GitHubTransientError(f"GitHub returned {response.status_code} for {path}")

    response.raise_for_status()
    log.info("github.request.success", duration_seconds=duration_seconds)
    return response.json()


async def list_repos(username: str) -> list[dict]:
    """Public repos for a GitHub username, newest-pushed first (GitHub's
    default order) - lets the model find the repo matching the project
    under discussion without a pre-existing project-to-repo mapping.
    """
    data = await _get_json(f"/users/{username}/repos")
    return [
        {
            "name": repo["name"],
            "description": repo.get("description"),
            "language": repo.get("language"),
        }
        for repo in data
    ]


async def list_repo_files(owner: str, repo: str, path: str = "") -> list[dict]:
    """Directory listing for a repo path (root if path is empty)."""
    data = await _get_json(f"/repos/{owner}/{repo}/contents/{path}")
    entries = data if isinstance(data, list) else [data]
    return [
        {"name": entry["name"], "path": entry["path"], "type": entry["type"]}
        for entry in entries
    ]


async def read_file(owner: str, repo: str, path: str) -> str:
    """Decoded text content of one file in a repo."""
    data = await _get_json(f"/repos/{owner}/{repo}/contents/{path}")
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
