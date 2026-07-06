import hashlib
import logging
import tempfile
import uuid
from typing import BinaryIO

from PIL import Image as PILImage
from PIL import UnidentifiedImageError

from app.models.image import Image
from app.repositories.base import ImageRepository
from app.services.errors import InvalidImageError, NotFoundError, PayloadTooLargeError
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

# 許可するMIMEと拡張子の対応
ALLOWED = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}
_CHUNK = 1024 * 1024  # 1MB


class ImageService:
    def __init__(
        self,
        repo: ImageRepository,
        storage: StorageBackend,
        max_bytes: int,
    ) -> None:
        self._repo = repo
        self._storage = storage
        self._max_bytes = max_bytes

    def upload(self, upload: BinaryIO, filename: str, content_type: str) -> tuple[Image, bool]:
        """画像を保存する。戻り値は (Image, is_new)。同一sha256があれば既存を返す(is_new=False)。"""
        if content_type not in ALLOWED:
            raise InvalidImageError(f"未対応の形式です: {content_type}")
        ext = ALLOWED[content_type]
        if not self._extension_matches(filename, content_type):
            raise InvalidImageError("拡張子とMIMEタイプが一致しません")

        # ストリームで一時ファイルへ保存しつつ sha256 とサイズを計算（メモリに全読みしない）
        digest = hashlib.sha256()
        size = 0
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = upload.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > self._max_bytes:
                    raise PayloadTooLargeError("ファイルサイズが上限を超えています")
                digest.update(chunk)
                tmp.write(chunk)

        if size == 0:
            raise InvalidImageError("空のファイルです")

        sha256 = digest.hexdigest()
        # 重複検知：同一内容が既にあれば保存せず既存を返す
        existing = self._repo.get_by_sha256(sha256)
        if existing is not None:
            logger.info("duplicate upload detected: sha256=%s", sha256[:12])
            return existing, False

        width, height = self._verify_and_measure(tmp_path)

        storage_key = f"uploads/{uuid.uuid4().hex}.{ext}"
        with open(tmp_path, "rb") as f:
            self._storage.save_stream(storage_key, f)

        image = self._repo.create(
            storage_key=storage_key,
            original_filename=filename,
            content_type=content_type,
            size=size,
            width=width,
            height=height,
            sha256=sha256,
        )
        logger.info("image uploaded: id=%s size=%s", image.id, size)
        return image, True

    def get(self, image_id: int) -> Image:
        image = self._repo.get(image_id)
        if image is None:
            raise NotFoundError("image not found")
        return image

    def list(self, page: int, limit: int, sort: str, order: str):
        return self._repo.list(page, limit, sort, order)

    def delete(self, image_id: int) -> None:
        image = self.get(image_id)
        # ストレージ実体も削除（存在しなくてもエラーにしない）
        self._storage.delete(image.storage_key)
        if image.thumbnail_key:
            self._storage.delete(image.thumbnail_key)
        self._repo.soft_delete(image)

    def open_file(self, image_id: int) -> tuple[BinaryIO, str]:
        image = self.get(image_id)
        return self._storage.open(image.storage_key), image.content_type

    def open_thumbnail(self, image_id: int) -> tuple[BinaryIO, str]:
        image = self.get(image_id)
        # 未生成ならオリジナルで代替
        if image.thumbnail_key and self._storage.exists(image.thumbnail_key):
            return self._storage.open(image.thumbnail_key), "image/jpeg"
        return self._storage.open(image.storage_key), image.content_type

    # --- helpers ---
    @staticmethod
    def _extension_matches(filename: str, content_type: str) -> bool:
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        # jpg/jpeg は同一扱い
        aliases = {"jpeg": "jpg"}
        ext = aliases.get(ext, ext)
        return ext == ALLOWED[content_type]

    @staticmethod
    def _verify_and_measure(path: str) -> tuple[int | None, int | None]:
        # Pillowで本当に画像として開けるか検証（拡張子/MIME偽装対策）
        try:
            with PILImage.open(path) as im:
                im.verify()  # 破損/非画像を検出（verify後は再利用不可）
            with PILImage.open(path) as im2:
                return im2.width, im2.height
        except (UnidentifiedImageError, OSError) as e:
            raise InvalidImageError("画像として読み込めません") from e
