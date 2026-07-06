import io

from PIL import Image as PILImage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.image import STATUS_READY
from app.repositories.sqlalchemy_image_repository import SQLAlchemyImageRepository
from app.services.thumbnail import generate_thumbnail
from app.storage.local import LocalStorage


def _setup(tmp_path):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    storage = LocalStorage(str(tmp_path / "s"))
    return session, storage


def test_generate_thumbnail_sets_ready(tmp_path) -> None:
    session, storage = _setup(tmp_path)
    repo = SQLAlchemyImageRepository(session)

    # 原本を保存
    buf = io.BytesIO()
    PILImage.new("RGB", (400, 200), (0, 128, 255)).save(buf, format="PNG")
    storage.save_bytes("uploads/x.png", buf.getvalue())
    image = repo.create(
        storage_key="uploads/x.png",
        original_filename="x.png",
        content_type="image/png",
        size=buf.tell(),
        width=400,
        height=200,
        sha256="a" * 64,
    )

    generate_thumbnail(storage, repo, image.id, 256)

    refreshed = repo.get(image.id)
    assert refreshed.status == STATUS_READY
    assert refreshed.thumbnail_key is not None
    assert storage.exists(refreshed.thumbnail_key)

    # サムネイルは256x256に統一されている
    with storage.open(refreshed.thumbnail_key) as f:
        thumb = PILImage.open(f)
        assert thumb.size == (256, 256)


def test_thumbnail_strips_exif(tmp_path) -> None:
    session, storage = _setup(tmp_path)
    repo = SQLAlchemyImageRepository(session)

    # EXIF付きJPEGを作成
    im = PILImage.new("RGB", (300, 300), (10, 20, 30))
    exif = im.getexif()
    exif[0x0110] = "TestCamera"  # Model
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif)
    storage.save_bytes("uploads/y.jpg", buf.getvalue())
    image = repo.create(
        storage_key="uploads/y.jpg",
        original_filename="y.jpg",
        content_type="image/jpeg",
        size=buf.tell(),
        width=300,
        height=300,
        sha256="b" * 64,
    )

    generate_thumbnail(storage, repo, image.id, 128)

    refreshed = repo.get(image.id)
    with storage.open(refreshed.thumbnail_key) as f:
        thumb = PILImage.open(f)
        assert len(dict(thumb.getexif())) == 0  # EXIFが除去されている


def test_storage_health_check(tmp_path) -> None:
    storage = LocalStorage(str(tmp_path / "h"))
    assert storage.health_check() is True


def test_storage_rejects_traversal(tmp_path) -> None:
    storage = LocalStorage(str(tmp_path / "t"))
    try:
        storage.save_bytes("../escape.txt", b"x")
        raise AssertionError("should have rejected traversal")
    except ValueError:
        pass
