import io
import logging

from PIL import Image as PILImage
from PIL import ImageOps

from app.models.image import STATUS_FAILED, STATUS_PROCESSING, STATUS_READY
from app.repositories.base import ImageRepository
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)


def generate_thumbnail(
    storage: StorageBackend,
    repo: ImageRepository,
    image_id: int,
    size: int,
) -> None:
    """バックグラウンドで実行するサムネイル生成。

    - EXIFの向きを反映しつつ EXIF自体は除去（新規JPEGとして保存 = メタデータを引き継がない）
    - ImageOps.fit で size×size に統一
    - 状態を PROCESSING → READY / FAILED に更新
    """
    image = repo.get(image_id)
    if image is None:
        return
    repo.update(image, status=STATUS_PROCESSING)
    try:
        with storage.open(image.storage_key) as f:
            pil = PILImage.open(f)
            pil = ImageOps.exif_transpose(pil)  # 向きを補正
            pil = pil.convert("RGB")  # JPEG保存のため
            thumb = ImageOps.fit(pil, (size, size))
            buf = io.BytesIO()
            thumb.save(buf, format="JPEG", quality=85)  # exifを渡さない=除去
        thumb_key = f"thumbnails/{image.storage_key.split('/')[-1].rsplit('.', 1)[0]}.jpg"
        storage.save_bytes(thumb_key, buf.getvalue())
        repo.update(image, thumbnail_key=thumb_key, status=STATUS_READY)
        logger.info("thumbnail generated: image_id=%s", image_id)
    except Exception:
        logger.exception("thumbnail generation failed: image_id=%s", image_id)
        repo.update(image, status=STATUS_FAILED)
