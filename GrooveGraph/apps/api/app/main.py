import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.observability import ObservabilityMiddleware, RateLimitMiddleware, configure_logging, configure_otel_if_available, metrics
from app.privacy import TokenRedactionFilter
from app.routes import router

configure_logging()
logging.getLogger().addFilter(TokenRedactionFilter())
configure_otel_if_available()

app = FastAPI(title="GrooveGraph API", version="0.1.0")
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_requests_per_minute)
app.add_middleware(ObservabilityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "GrooveGraph API"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics_endpoint() -> str:
    return metrics.render_prometheus()


app.include_router(router)
