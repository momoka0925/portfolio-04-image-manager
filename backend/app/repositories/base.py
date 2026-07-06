from abc import ABC, abstractmethod

from app.models.image import Image


class ImageRepository(ABC):
    @abstractmethod
    def create(self, **fields) -> Image: ...

    @abstractmethod
    def get(self, image_id: int) -> Image | None: ...

    @abstractmethod
    def get_by_sha256(self, sha256: str) -> Image | None: ...

    @abstractmethod
    def list(
        self, page: int, limit: int, sort: str, order: str
    ) -> tuple[list[Image], int]: ...

    @abstractmethod
    def update(self, image: Image, **fields) -> Image: ...

    @abstractmethod
    def soft_delete(self, image: Image) -> None: ...
