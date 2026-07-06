import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import get_storage
from app.api.images import router as images_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.response import ApiResponse
from app.services.errors import InvalidImageError, NotFoundError, PayloadTooLargeError

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Image Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images_router)


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse(success=False, message=message).model_dump(),
    )


@app.exception_handler(InvalidImageError)
def _invalid(request: Request, exc: InvalidImageError) -> JSONResponse:
    return _error(400, str(exc))


@app.exception_handler(PayloadTooLargeError)
def _too_large(request: Request, exc: PayloadTooLargeError) -> JSONResponse:
    return _error(413, str(exc))


@app.exception_handler(NotFoundError)
def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error(404, "対象が見つかりません")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/storage")
def health_storage() -> JSONResponse:
    # Storage書き込みとDB接続を個別に確認する
    storage_ok = get_storage().health_check()
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False
    ok = storage_ok and db_ok
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"storage": storage_ok, "database": db_ok},
    )
