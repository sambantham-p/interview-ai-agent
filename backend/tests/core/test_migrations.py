import threading

import pytest
from alembic.script import ScriptDirectory
from pytest_mock import MockerFixture

from app.core.migrations import MIGRATIONS_DIR, build_alembic_config, run_migrations


def test_alembic_config_points_at_the_migrations_directory() -> None:
    config = build_alembic_config()

    assert (MIGRATIONS_DIR / "env.py").is_file()
    assert config.get_main_option("script_location") == str(MIGRATIONS_DIR)


def test_alembic_config_has_no_ini_file() -> None:
    # env.py calls logging.config.fileConfig() whenever an ini file is set,
    # which would replace the app's structlog handlers.
    assert build_alembic_config().config_file_name is None


def test_migration_history_has_a_single_head() -> None:
    # Two heads would make `upgrade head` fail at startup.
    heads = ScriptDirectory.from_config(build_alembic_config()).get_heads()

    assert len(heads) == 1


async def test_run_migrations_upgrades_to_head_off_the_event_loop_thread(
    mocker: MockerFixture,
) -> None:
    loop_thread = threading.get_ident()
    upgrade_thread: list[int] = []
    fake_upgrade = mocker.patch(
        "app.core.migrations.command.upgrade",
        side_effect=lambda *_: upgrade_thread.append(threading.get_ident()),
    )

    await run_migrations()

    fake_upgrade.assert_called_once()
    config, revision = fake_upgrade.call_args.args
    assert config.get_main_option("script_location") == str(MIGRATIONS_DIR)
    assert revision == "head"
    assert upgrade_thread != [loop_thread]


async def test_run_migrations_reraises_failures(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.migrations.command.upgrade",
        side_effect=RuntimeError("cannot reach database"),
    )

    with pytest.raises(RuntimeError, match="cannot reach database"):
        await run_migrations()
