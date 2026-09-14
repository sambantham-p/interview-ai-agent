from pytest_mock import MockerFixture

from app.core.github_tools import GITHUB_TOOL_DISPATCH, GITHUB_TOOLS


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
