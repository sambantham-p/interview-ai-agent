import importlib

import pytest

SHIM_MODULES = ["auth", "interview", "jd", "judge", "response", "resume", "voice"]


@pytest.mark.parametrize("name", SHIM_MODULES)
def test_schema_shim_re_exports_the_dto_module(name: str) -> None:
    shim = importlib.import_module(f"app.schemas.{name}")
    dto = importlib.import_module(f"app.dto.{name}")

    public_dto_names = [n for n in vars(dto) if not n.startswith("_")]
    exported = [n for n in public_dto_names if hasattr(shim, n)]

    assert exported, f"app.schemas.{name} re-exports nothing from app.dto.{name}"
