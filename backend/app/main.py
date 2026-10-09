from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.api import health, runs, validate
from app.api.errors import register_error_handlers
from app.services import run_service
from app.services.executor import get_executor, shutdown_executor


@asynccontextmanager
async def lifespan(_: FastAPI):  # noqa: ANN201
    run_service.mark_stale_runs_failed()
    get_executor()
    yield
    shutdown_executor()


app = FastAPI(title="U-Line Balancing API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):  # noqa: ANN001, ANN201
    # Basic guard using the declared length (chunked uploads are not covered).
    length = request.headers.get("content-length")
    if length is not None and length.isdigit() and int(length) > config.MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": {"code": "payload_too_large", "message": "Request body is too large.", "details": []}},
        )
    return await call_next(request)


# Added after the size limit so CORS headers are also present on its 413 responses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

register_error_handlers(app)
app.include_router(health.router)
app.include_router(validate.router)
app.include_router(runs.router)
