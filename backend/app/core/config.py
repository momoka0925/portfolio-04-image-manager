from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./images.db"

    # ローカルストレージの保存先
    storage_dir: str = "./storage_data"

    # アップロード上限（バイト）。既定10MB
    max_upload_bytes: int = 10 * 1024 * 1024

    # サムネイルの一辺(px)
    thumbnail_size: int = 256

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
