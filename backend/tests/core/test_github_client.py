from collections.abc import Iterator

import httpx
import pytest
from pytest_mock import MockerFixture

from app.constants.github import GITHUB_API_BASE_URL
from app.core.github_client import (
    GitHubNotFoundError,
    GitHubTransientError,
    extract_github_username,
    get_github_client,
    list_repo_files,
    list_repos,
    parse_github_repo_url,
    read_file,
)


@pytest.fixture(autouse=True)
def _clear_client_cache() -> Iterator[None]:
    get_github_client.cache_clear()
    yield
    get_github_client.cache_clear()


def test_get_github_client_is_always_unauthenticated() -> None:
    client = get_github_client()

    assert str(client.base_url) == GITHUB_API_BASE_URL
    assert "Authorization" not in client.headers
    assert client.headers["Accept"] == "application/vnd.github+json"


def test_get_github_client_is_cached() -> None:
    assert get_github_client() is get_github_client()


def _fake_response(*, status_code: int, json_data=None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://api.github.com/x"),
    )


def _mock_client(mocker: MockerFixture, response: httpx.Response):
    fake_client = mocker.AsyncMock()
    fake_client.get = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.github_client.get_github_client", return_value=fake_client)
    return fake_client


class TestExtractGithubUsername:
    def test_extracts_username_from_profile_url(self) -> None:
        assert extract_github_username("https://github.com/octocat") == "octocat"

    def test_handles_trailing_slash(self) -> None:
        assert extract_github_username("https://github.com/octocat/") == "octocat"

    def test_returns_none_for_missing_url(self) -> None:
        assert extract_github_username(None) is None
        assert extract_github_username("") is None

    def test_returns_none_for_non_github_url(self) -> None:
        assert extract_github_username("https://gitlab.com/octocat") is None

    def test_returns_none_for_bare_domain(self) -> None:
        assert extract_github_username("https://github.com/") is None


class TestParseGithubRepoUrl:
    def test_parses_owner_and_repo(self) -> None:
        assert parse_github_repo_url("https://github.com/octocat/hello-world") == (
            "octocat",
            "hello-world",
        )

    def test_strips_trailing_slash(self) -> None:
        assert parse_github_repo_url("https://github.com/octocat/hello-world/") == (
            "octocat",
            "hello-world",
        )

    def test_strips_dot_git_suffix(self) -> None:
        assert parse_github_repo_url("https://github.com/octocat/hello-world.git") == (
            "octocat",
            "hello-world",
        )

    def test_returns_none_for_missing_url(self) -> None:
        assert parse_github_repo_url(None) is None
        assert parse_github_repo_url("") is None

    def test_returns_none_for_profile_url_with_no_repo_segment(self) -> None:
        assert parse_github_repo_url("https://github.com/octocat") is None

    def test_returns_none_for_non_github_url(self) -> None:
        assert parse_github_repo_url("https://gitlab.com/octocat/repo") is None


async def test_list_repos_returns_name_description_language(
    mocker: MockerFixture,
) -> None:
    _mock_client(
        mocker,
        _fake_response(
            status_code=200,
            json_data=[
                {
                    "name": "hello-world",
                    "description": "My first repo",
                    "language": "Python",
                    "extra_field": "ignored",
                }
            ],
        ),
    )

    result = await list_repos("octocat")

    assert result == [
        {"name": "hello-world", "description": "My first repo", "language": "Python"}
    ]


async def test_list_repo_files_returns_directory_listing(
    mocker: MockerFixture,
) -> None:
    _mock_client(
        mocker,
        _fake_response(
            status_code=200,
            json_data=[
                {"name": "main.py", "path": "src/main.py", "type": "file"},
                {"name": "utils", "path": "src/utils", "type": "dir"},
            ],
        ),
    )

    result = await list_repo_files("octocat", "hello-world", "src")

    assert result == [
        {"name": "main.py", "path": "src/main.py", "type": "file"},
        {"name": "utils", "path": "src/utils", "type": "dir"},
    ]


async def test_list_repo_files_wraps_a_single_file_response_in_a_list(
    mocker: MockerFixture,
) -> None:
    # GitHub returns a dict (not a list) when `path` points at a file, not
    # a directory - normalize to the same list-of-entries shape either way.
    _mock_client(
        mocker,
        _fake_response(
            status_code=200,
            json_data={"name": "README.md", "path": "README.md", "type": "file"},
        ),
    )

    result = await list_repo_files("octocat", "hello-world", "README.md")

    assert result == [{"name": "README.md", "path": "README.md", "type": "file"}]


async def test_read_file_decodes_base64_content(mocker: MockerFixture) -> None:
    import base64

    encoded = base64.b64encode(b"print('hello')").decode()
    _mock_client(
        mocker,
        _fake_response(status_code=200, json_data={"content": encoded}),
    )

    result = await read_file("octocat", "hello-world", "main.py")

    assert result == "print('hello')"


async def test_get_json_raises_not_found_on_404(mocker: MockerFixture) -> None:
    _mock_client(mocker, _fake_response(status_code=404))

    with pytest.raises(GitHubNotFoundError):
        await list_repos("octocat")


async def test_get_json_raises_transient_error_on_rate_limit(
    mocker: MockerFixture,
) -> None:
    _mock_client(mocker, _fake_response(status_code=403))

    with pytest.raises(GitHubTransientError):
        await list_repos("octocat")


async def test_get_json_raises_transient_error_on_server_error(
    mocker: MockerFixture,
) -> None:
    _mock_client(mocker, _fake_response(status_code=500))

    with pytest.raises(GitHubTransientError):
        await list_repos("octocat")


async def test_get_json_raises_transient_error_on_network_failure(
    mocker: MockerFixture,
) -> None:
    fake_client = mocker.AsyncMock()
    fake_client.get = mocker.AsyncMock(
        side_effect=httpx.ConnectError("connection refused")
    )
    mocker.patch("app.core.github_client.get_github_client", return_value=fake_client)

    with pytest.raises(GitHubTransientError):
        await list_repos("octocat")
