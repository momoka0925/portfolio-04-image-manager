from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.image import Image
from app.repositories.base import ImageRepository

_SORT_COLUMNS = {"created_at": Image.created_at, "size": Image.size}


class SQLAlchemyImageRepository(ImageRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, **fields) -> Image:
        image = Image(**fields)
        self._db.add(image)
        self._db.commit()
        self._db.refresh(image)
        return image

    def get(self, image_id: int) -> Image | None:
        return self._db.scalar(
            select(Image).where(Image.id == image_id, Image.deleted_at.is_(None))
        )

    def get_by_sha256(self, sha256: str) -> Image | None:
        return self._db.scalar(
            select(Image).where(Image.sha256 == sha256, Image.deleted_at.is_(None))
        )

    def list(self, page: int, limit: int, sort: str, order: str) -> tuple[list[Image], int]:
        column = _SORT_COLUMNS.get(sort, Image.created_at)
        ordering = column.asc() if order == "asc" else column.desc()

        total = (
            self._db.scalar(
                select(func.count()).select_from(Image).where(Image.deleted_at.is_(None))
            )
            or 0
        )
        items = list(
            self._db.scalars(
                select(Image)
                .where(Image.deleted_at.is_(None))
                .order_by(ordering, Image.id.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        return items, total

    def update(self, image: Image, **fields) -> Image:
        for key, value in fields.items():
            setattr(image, key, value)
        self._db.commit()
        self._db.refresh(image)
        return image

    def soft_delete(self, image: Image) -> None:
        image.deleted_at = datetime.now(timezone.utc)
        self._db.commit()
