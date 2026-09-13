from prometheus_client import Counter, Gauge, Histogram, Info

HTTP_REQUESTS = Counter(
    "parallax_http_requests_total",
    "Total HTTP requests handled by the API",
    ("method", "path", "status"),
)

HTTP_DURATION = Histogram(
    "parallax_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
)

HTTP_FAILURES = Counter(
    "parallax_http_failures_total",
    "Unhandled API request failures",
    ("method", "path"),
)

API_READY = Gauge("parallax_api_ready", "Whether the API process is serving requests")
BUILD_INFO = Info("parallax_build", "Parallax backend build information")
BUILD_INFO.info({"version": "0.1.0", "runtime": "python"})
API_READY.set(1)
