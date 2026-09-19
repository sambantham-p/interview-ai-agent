from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    message: str


class APIResponse(BaseModel):
    success: bool
    status: str
    status_code: int
    data: Any | None = None
    error: ErrorDetail | None = None
