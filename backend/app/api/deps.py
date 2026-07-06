from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.repositories.sqlalchemy_image_repository import SQLAlchemyImageRepository
from app.services.image_service import ImageService
from app.storage.base import StorageBackend
from app.storage.local import LocalStorage

DbDep = Annotated[Session, Depends(get_db)]


@lru_cache
def get_storage() -> StorageBackend:
    # ストレージはプロセスで共有（実装は差し替え可能）
    return LocalStorage(settings.storage_dir)


def get_image_service(db: DbDep) -> ImageService:
    return ImageService(
        repo=SQLAlchemyImageRepository(db),
        storage=get_storage(),
        max_bytes=settings.max_upload_bytes,
    )
