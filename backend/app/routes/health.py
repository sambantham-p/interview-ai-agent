import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.constants.app import SERVICE_NAME
from app.constants.health import HEALTH_STATUS_HEALTHY, HEALTH_STATUS_UNHEALTHY
from app.core.responses import error_response, success_response

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> JSONResponse:
    try:
        payload = {"service": SERVICE_NAME, "health": HEALTH_STATUS_HEALTHY}
        return success_response(data=payload, status_code=httpx.codes.OK)
    except Exception:  # noqa: BLE001 - liveness check: any failure here means unhealthy
        payload = {"service": SERVICE_NAME, "health": HEALTH_STATUS_UNHEALTHY}
        return error_response(
            message="Service unhealthy",
            status_code=httpx.codes.INTERNAL_SERVER_ERROR,
            data=payload,
        )
