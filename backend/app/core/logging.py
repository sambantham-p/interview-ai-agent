import logging
import sys

import structlog

_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.CallsiteParameterAdder(
        {
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.FUNC_NAME,
        }
    ),
]


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog and stdlib logging together, once, at process
    startup. Every log line - whether it comes from this app's own
    `structlog.get_logger()` calls or from a library still using stdlib
    `logging` (Uvicorn, SQLAlchemy, ...) - is routed through the same
    processor pipeline.

    Rendered as colored, human-readable text when stdout is a real
    terminal (local dev); flat JSON otherwise (piped to a file, running
    under a process manager on Render, etc. - anywhere a log aggregator
    would actually want to parse it).
    """
    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )

    if sys.stdout.isatty():
        # format_exc_info would pre-render exc_info into a plain string,
        # leaving ConsoleRenderer's own RichTracebackFormatter nothing
        # left to work with - so it's deliberately skipped here; the
        # renderer handles raw exc_info itself for the colored traceback.
        render_processors: list[structlog.typing.Processor] = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    theme="monokai"
                ),
            ),
        ]
    else:
        render_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=render_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # Uvicorn configures "uvicorn"/"uvicorn.access"/"uvicorn.error" with
    # their own handlers and propagate=False, so replacing the root
    # logger's handlers alone never reaches them - their access/error
    # lines would stay in Uvicorn's own plain-text format instead of
    # joining the same JSON pipeline. Strip their handlers and let them
    # propagate up to the root handler above instead.
    for uvicorn_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
