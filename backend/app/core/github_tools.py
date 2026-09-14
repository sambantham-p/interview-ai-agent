"""Bridges the plain-Python GitHub client (app/core/github_client.py) to
Gemini's native function-calling types - client is HTTP I/O, this is the
Gemini-facing schema/dispatch layer.

The scope guardrail limiting the model to only named projects lives in
the Phase 2 system instruction, not here - these tools have no per-project
repo mapping to check against in code.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from google.genai import types

from app.core.github_client import list_repo_files, list_repos, read_file

GITHUB_TOOLS: list[types.Tool] = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="list_repos",
                description=(
                    "List a GitHub user's public repositories (name, "
                    "description, language). Use this only to find the repo "
                    "matching a project the candidate has already named - "
                    "never to browse for other repos to bring up unprompted."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "username": types.Schema(
                            type=types.Type.STRING,
                            description="The GitHub username to list repos for.",
                        )
                    },
                    required=["username"],
                ),
            ),
            types.FunctionDeclaration(
                name="list_repo_files",
                description=(
                    "List the files/directories at a path in a GitHub repo "
                    "(root if path is omitted)."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "owner": types.Schema(
                            type=types.Type.STRING, description="Repo owner/username."
                        ),
                        "repo": types.Schema(
                            type=types.Type.STRING, description="Repo name."
                        ),
                        "path": types.Schema(
                            type=types.Type.STRING,
                            description="Directory path; omit for the repo root.",
                        ),
                    },
                    required=["owner", "repo"],
                ),
            ),
            types.FunctionDeclaration(
                name="read_file",
                description="Read the text content of one file in a GitHub repo.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "owner": types.Schema(
                            type=types.Type.STRING, description="Repo owner/username."
                        ),
                        "repo": types.Schema(
                            type=types.Type.STRING, description="Repo name."
                        ),
                        "path": types.Schema(
                            type=types.Type.STRING,
                            description="File path within the repo.",
                        ),
                    },
                    required=["owner", "repo", "path"],
                ),
            ),
        ]
    )
]


async def _list_repo_files(**kwargs: Any) -> list[dict]:
    return await list_repo_files(
        owner=kwargs["owner"], repo=kwargs["repo"], path=kwargs.get("path", "")
    )


GITHUB_TOOL_DISPATCH: dict[str, Callable[..., Awaitable[Any]]] = {
    "list_repos": lambda **kwargs: list_repos(username=kwargs["username"]),
    "list_repo_files": _list_repo_files,
    "read_file": lambda **kwargs: read_file(
        owner=kwargs["owner"], repo=kwargs["repo"], path=kwargs["path"]
    ),
}
