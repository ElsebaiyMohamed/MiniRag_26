import os
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, \
    CollectorRegistry, multiprocess
from starlette.types import ASGIApp, Receive, Scope, Send

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"])
DOCUMENT_PROCESSING_DURATION = Histogram(
    "document_processing_duration_seconds",
    "Time spent loading and splitting uploaded documents",
    ["file_type", "outcome"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)

class PrometheusMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start_time = time.time()

        status_code = 500

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                nonlocal status_code
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start_time

            # Use the route path template if available, else fallback to URL path
            route = scope.get("route")
            endpoint = (
                route.path
                if route and hasattr(route, "path")
                else request.url.path
            )

            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)

            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=status_code,
            ).inc()
def setup_metrics(app: FastAPI):
    app.add_middleware(PrometheusMiddleware)

    prometheus_multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        if prometheus_multiproc_dir:
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            data = generate_latest(registry)
        else:
            data = generate_latest()
        return Response(data, media_type=CONTENT_TYPE_LATEST)
