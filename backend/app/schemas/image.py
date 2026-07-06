from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.image import STATUS_READY


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    content_type: str
    size: int
    width: int | None
    height: int | None
    sha256: str
    status: str
    thumbnail_key: str | None
    created_at: datetime

    @computed_field
    @property
    def has_thumbnail(self) -> bool:
        return self.status == STATUS_READY and self.thumbnail_key is not None


class ImagePage(BaseModel):
    items: list[ImageOut]
    total: int
    page: int
    limit: int
