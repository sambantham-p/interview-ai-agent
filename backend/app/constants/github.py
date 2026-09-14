GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_CLIENT_TIMEOUT_SECONDS = 15.0
GITHUB_RATE_LIMIT_STATUS_CODE = 403

# Bounds tool-loop latency/cost for a live interview turn
GITHUB_TOOL_LOOP_MAX_ROUNDS = 4

# Cap GitHub calls per session to protect the shared 60/hr unauthenticated
GITHUB_CALL_BUDGET_PER_SESSION = 15
