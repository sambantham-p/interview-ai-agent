import asyncio
from pathlib import Path

import structlog
from alembic import command
from alembic.config import Config

logger = structlog.get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def build_alembic_config() -> Config:
    """Alembic config built in code, with no alembic.ini behind it.

    migrations/env.py calls logging.config.fileConfig() whenever the
    config has an ini file, which would replace this app's structlog
    handlers with alembic.ini's console handler partway through startup.
    With no ini file that call is skipped. The database URL doesn't come
    from the config either - env.py reads it via app.core.db.
    """
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


async def run_migrations() -> None:
    """Bring the database to the latest revision (`alembic upgrade head`).

    env.py drives its own event loop with asyncio.run(), which can't be
    started from inside the running server loop, so the upgrade runs in a
    worker thread. env.py also disposes the shared engine when it
    finishes, so the app's first query afterwards gets a fresh connection
    pool on the server loop.

    A failure is logged and re-raised: serving requests against a schema
    older than the code would only fail later, one request at a time.
    """
    logger.info("migrations_started")
    try:
        await asyncio.to_thread(command.upgrade, build_alembic_config(), "head")
    except Exception:
        logger.exception("migrations_failed")
        raise
    logger.info("migrations_finished")
