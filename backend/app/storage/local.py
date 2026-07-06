import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """ローカルディスクへの保存実装。

    key は "サブディレクトリ/ファイル名" 形式（例: "uploads/<uuid>.png"）。
    key は必ずアプリ生成のUUIDベースにし、外部入力のパスは受け付けない（パストラバーサル対策）。
    """

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # key に .. や絶対パスが混じっても base の外に出ないよう解決して検証する
        resolved = (self._base / key).resolve()
        if not str(resolved).startswith(str(self._base.resolve())):
            raise ValueError(f"invalid storage key: {key}")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    def save_stream(self, key: str, stream: BinaryIO) -> None:
        with open(self._path(key), "wb") as f:
            shutil.copyfileobj(stream, f)

    def save_bytes(self, key: str, data: bytes) -> None:
        with open(self._path(key), "wb") as f:
            f.write(data)

    def open(self, key: str) -> BinaryIO:
        return open(self._path(key), "rb")

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def health_check(self) -> bool:
        probe = f"_health/{uuid.uuid4().hex}"
        try:
            self.save_bytes(probe, b"ok")
            ok = self.exists(probe)
            self.delete(probe)
            return ok
        except OSError:
            return False
