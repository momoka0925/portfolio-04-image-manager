import logging
from collections.abc import Iterator
from typing import Annotated, BinaryIO

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import get_image_service, get_storage
from app.core.config import settings
from app.repositories.sqlalchemy_image_repository import SQLAlchemyImageRepository
from app.schemas.image import ImageOut, ImagePage
from app.schemas.response import ApiResponse
from app.services.image_service import ImageService
from app.services.thumbnail import generate_thumbnail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

ServiceDep = Annotated[ImageService, Depends(get_image_service)]


@router.post("", response_model=ApiResponse[ImageOut])
def upload_image(
    service: ServiceDep,
    background: BackgroundTasks,
    response: Response,
    file: UploadFile = File(...),
) -> ApiResponse[ImageOut]:
    image, is_new = service.upload(file.file, file.filename or "upload", file.content_type or "")
    if is_new:
        response.status_code = 201
        # サムネイル生成はレスポンス後にバックグラウンドで実行
        background.add_task(_run_thumbnail, image.id)
    else:
        response.status_code = 200
    return ApiResponse[ImageOut](success=True, data=ImageOut.model_validate(image))


def _run_thumbnail(image_id: int) -> None:
    # バックグラウンド用に独自のDBセッションを開く（リクエストのセッションは閉じられるため）。
    # バックグラウンド処理の失敗はワーカーに伝播させない。
    from app.db.session import SessionLocal

    try:
        db = SessionLocal()
        try:
            generate_thumbnail(
                get_storage(), SQLAlchemyImageRepository(db), image_id, settings.thumbnail_size
            )
        finally:
            db.close()
    except Exception:
        logger.exception("background thumbnail task failed: image_id=%s", image_id)


@router.get("", response_model=ApiResponse[ImagePage])
def list_images(
    service: ServiceDep,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at", pattern="^(created_at|size)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
) -> ApiResponse[ImagePage]:
    items, total = service.list(page, limit, sort, order)
    return ApiResponse[ImagePage](
        success=True,
        data=ImagePage(
            items=[ImageOut.model_validate(i) for i in items],
            total=total,
            page=page,
            limit=limit,
        ),
    )


@router.get("/{image_id}", response_model=ApiResponse[ImageOut])
def get_image(image_id: int, service: ServiceDep) -> ApiResponse[ImageOut]:
    return ApiResponse[ImageOut](success=True, data=ImageOut.model_validate(service.get(image_id)))


def _stream_and_close(stream: BinaryIO) -> Iterator[bytes]:
    # チャンクで配信し、最後に必ずハンドルを閉じる（Windowsでの削除ロック回避）
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


@router.get("/{image_id}/file")
def get_file(image_id: int, service: ServiceDep) -> StreamingResponse:
    stream, content_type = service.open_file(image_id)
    return StreamingResponse(_stream_and_close(stream), media_type=content_type)


@router.get("/{image_id}/thumbnail")
def get_thumbnail(image_id: int, service: ServiceDep) -> StreamingResponse:
    stream, content_type = service.open_thumbnail(image_id)
    return StreamingResponse(_stream_and_close(stream), media_type=content_type)


@router.delete("/{image_id}", response_model=ApiResponse[None])
def delete_image(image_id: int, service: ServiceDep) -> ApiResponse[None]:
    service.delete(image_id)
    return ApiResponse[None](success=True, message="Deleted")
