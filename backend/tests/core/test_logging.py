import json
import logging

import pytest
import structlog
from pytest_mock import MockerFixture

from app.core.logging import configure_logging


def test_configure_logging_sets_a_json_handler_on_root_logger() -> None:
    configure_logging()

    root_logger = logging.getLogger()

    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0].formatter, logging.Formatter)


def test_configure_logging_makes_uvicorn_loggers_propagate_to_root() -> None:
    configure_logging()

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        assert uvicorn_logger.handlers == []
        assert uvicorn_logger.propagate is True


def test_configure_logging_emits_flat_json_with_expected_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging()

    structlog.get_logger("test-logger").info("something happened", candidate_id=42)

    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert line["event"] == "something happened"
    assert line["candidate_id"] == 42
    assert line["level"] == "info"
    assert "timestamp" in line
    assert "filename" in line
    assert "lineno" in line


def test_configure_logging_uses_colored_console_output_on_a_real_terminal(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch("sys.stdout.isatty", return_value=True)
    configure_logging()

    structlog.get_logger("test-logger").info("something happened")

    out = capsys.readouterr().out
    assert "\x1b[" in out  # ANSI color codes present - not the JSON path
    assert "something happened" in out


def test_configure_logging_renders_exceptions_with_rich_locals_on_a_real_terminal(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch("sys.stdout.isatty", return_value=True)
    configure_logging()

    try:
        raise ZeroDivisionError("division by zero")
    except ZeroDivisionError:
        structlog.get_logger("test-logger").exception("math broke")

    out = capsys.readouterr().out
    assert "Traceback" in out
    assert "ZeroDivisionError" in out
