import pytest
from pytest_mock import MockerFixture

from app.core.github_tools import (
    GITHUB_TOOL_DISPATCH,
    GITHUB_TOOLS,
    build_scoped_github_dispatch,
)


def test_github_tools_declares_the_three_expected_functions() -> None:
    declared_names = {fd.name for fd in GITHUB_TOOLS[0].function_declarations}

    assert declared_names == {"list_repos", "list_repo_files", "read_file"}


def test_dispatch_has_an_entry_for_every_declared_tool() -> None:
    declared_names = {fd.name for fd in GITHUB_TOOLS[0].function_declarations}

    assert set(GITHUB_TOOL_DISPATCH.keys()) == declared_names


async def test_dispatch_list_repos_calls_client_with_username(
    mocker: MockerFixture,
) -> None:
    fake_list_repos = mocker.patch(
        "app.core.github_tools.list_repos",
        new_callable=mocker.AsyncMock,
        return_value=[{"name": "repo1"}],
    )

    result = await GITHUB_TOOL_DISPATCH["list_repos"](username="octocat")

    fake_list_repos.assert_awaited_once_with(username="octocat")
    assert result == [{"name": "repo1"}]


async def test_dispatch_list_repo_files_defaults_path_to_root(
    mocker: MockerFixture,
) -> None:
    fake_list_repo_files = mocker.patch(
        "app.core.github_tools.list_repo_files",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )

    await GITHUB_TOOL_DISPATCH["list_repo_files"](owner="octocat", repo="hello-world")

    fake_list_repo_files.assert_awaited_once_with(
        owner="octocat", repo="hello-world", path=""
    )


async def test_dispatch_list_repo_files_passes_through_explicit_path(
    mocker: MockerFixture,
) -> None:
    fake_list_repo_files = mocker.patch(
        "app.core.github_tools.list_repo_files",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )

    await GITHUB_TOOL_DISPATCH["list_repo_files"](
        owner="octocat", repo="hello-world", path="src"
    )

    fake_list_repo_files.assert_awaited_once_with(
        owner="octocat", repo="hello-world", path="src"
    )


async def test_dispatch_read_file_calls_client_with_all_args(
    mocker: MockerFixture,
) -> None:
    fake_read_file = mocker.patch(
        "app.core.github_tools.read_file",
        new_callable=mocker.AsyncMock,
        return_value="file contents",
    )

    result = await GITHUB_TOOL_DISPATCH["read_file"](
        owner="octocat", repo="hello-world", path="main.py"
    )

    fake_read_file.assert_awaited_once_with(
        owner="octocat", repo="hello-world", path="main.py"
    )
    assert result == "file contents"


async def test_scoped_dispatch_allows_the_candidates_own_username(
    mocker: MockerFixture,
) -> None:
    fake_list_repos = mocker.patch(
        "app.core.github_tools.list_repos",
        new_callable=mocker.AsyncMock,
        return_value=[{"name": "repo1"}],
    )
    dispatch = build_scoped_github_dispatch("octocat")

    result = await dispatch["list_repos"](username="octocat")

    fake_list_repos.assert_awaited_once_with(username="octocat")
    assert result == [{"name": "repo1"}]


async def test_scoped_dispatch_is_case_insensitive(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.github_tools.list_repos",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )
    dispatch = build_scoped_github_dispatch("OctoCat")

    await dispatch["list_repos"](username="octocat")


async def test_scoped_dispatch_rejects_a_different_username(
    mocker: MockerFixture,
) -> None:
    fake_list_repos = mocker.patch(
        "app.core.github_tools.list_repos",
        new_callable=mocker.AsyncMock,
    )
    dispatch = build_scoped_github_dispatch("octocat")

    with pytest.raises(ValueError, match="Not permitted"):
        await dispatch["list_repos"](username="torvalds")

    fake_list_repos.assert_not_awaited()


async def test_scoped_dispatch_rejects_a_different_owner_for_list_repo_files(
    mocker: MockerFixture,
) -> None:
    fake_list_repo_files = mocker.patch(
        "app.core.github_tools.list_repo_files",
        new_callable=mocker.AsyncMock,
    )
    dispatch = build_scoped_github_dispatch("octocat")

    with pytest.raises(ValueError, match="Not permitted"):
        await dispatch["list_repo_files"](owner="torvalds", repo="linux")

    fake_list_repo_files.assert_not_awaited()


async def test_scoped_dispatch_rejects_a_different_owner_for_read_file(
    mocker: MockerFixture,
) -> None:
    fake_read_file = mocker.patch(
        "app.core.github_tools.read_file",
        new_callable=mocker.AsyncMock,
    )
    dispatch = build_scoped_github_dispatch("octocat")

    with pytest.raises(ValueError, match="Not permitted"):
        await dispatch["read_file"](owner="torvalds", repo="linux", path="README.md")

    fake_read_file.assert_not_awaited()


async def test_scoped_dispatch_forwards_list_repo_files_for_the_own_account(
    mocker: MockerFixture,
) -> None:
    fake = mocker.patch(
        "app.core.github_tools.list_repo_files",
        new_callable=mocker.AsyncMock,
        return_value=[{"name": "README.md"}],
    )
    dispatch = build_scoped_github_dispatch("octocat")

    result = await dispatch["list_repo_files"](owner="octocat", repo="r")

    fake.assert_awaited_once_with(owner="octocat", repo="r", path="")
    assert result == [{"name": "README.md"}]


async def test_scoped_dispatch_forwards_read_file_for_the_own_account(
    mocker: MockerFixture,
) -> None:
    fake = mocker.patch(
        "app.core.github_tools.read_file",
        new_callable=mocker.AsyncMock,
        return_value="content",
    )
    dispatch = build_scoped_github_dispatch("octocat")

    result = await dispatch["read_file"](owner="octocat", repo="r", path="README.md")

    fake.assert_awaited_once_with(owner="octocat", repo="r", path="README.md")
    assert result == "content"


async def test_scoped_dispatch_rejects_other_owners_for_file_tools(
    mocker: MockerFixture,
) -> None:
    dispatch = build_scoped_github_dispatch("octocat")

    with pytest.raises(ValueError, match="Not permitted"):
        await dispatch["list_repo_files"](owner="someone-else", repo="r")
    with pytest.raises(ValueError, match="Not permitted"):
        await dispatch["read_file"](owner="someone-else", repo="r", path="x")
