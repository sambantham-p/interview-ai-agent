from app.constants.app import API_V1_PREFIX

REQUEST_ID_HEADER = "X-Request-ID"


TRACE_ID_HEADER = "X-Trace-ID"

REQUEST_ID_OPTIONAL_PATHS = frozenset(
    {
        f"{API_V1_PREFIX}/health",
        f"{API_V1_PREFIX}/docs",
        f"{API_V1_PREFIX}/redoc",
        f"{API_V1_PREFIX}/openapi.json",
    }
)
