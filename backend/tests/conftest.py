import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_image_service, get_storage
from app.db.base import Base
from app.main import app
from app.repositories.sqlalchemy_image_repository import SQLAlchemyImageRepository
from app.services.image_service import ImageService
from app.storage.local import LocalStorage


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = TestingSession()
    storage = LocalStorage(str(tmp_path / "storage"))

    def _override_service() -> ImageService:
        return ImageService(SQLAlchemyImageRepository(session), storage, max_bytes=1024 * 1024)

    # /health/storage 等が使う共有ストレージも上書き
    get_storage.cache_clear()
    app.dependency_overrides[get_image_service] = _override_service
    app.dependency_overrides[get_storage] = lambda: storage

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)


def make_png(color=(255, 0, 0), size=(100, 80)) -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()
