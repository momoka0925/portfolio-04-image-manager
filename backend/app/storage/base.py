from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    """ファイル保存先の抽象インターフェース。

    Service はこの抽象に依存する。LocalStorage を将来 S3Storage / R2Storage へ
    差し替えても Service は変更不要（P02のCache・P03のRepositoryと同じ思想）。
    """

    @abstractmethod
    def save_stream(self, key: str, stream: BinaryIO) -> None:
        """ストリームを key に保存する（メモリに全読みしない）。"""

    @abstractmethod
    def save_bytes(self, key: str, data: bytes) -> None:
        """バイト列を key に保存する（サムネイル等の小さいデータ用）。"""

    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        """key の読み込み用ストリームを返す。"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """key を削除する（存在しなくてもエラーにしない）。"""

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def health_check(self) -> bool:
        """書き込み/削除が可能かを確認する（/health/storage 用）。"""
