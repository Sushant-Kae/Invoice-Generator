"""
Application configuration using pydantic-settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/shah_invoices"

    # Security
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # File Storage
    UPLOAD_DIR: str = "uploads"
    GENERATED_DIR: str = "generated"
    TEMPLATE_DIR: str = "templates"

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 20

    # CORS — stored as plain string in .env, parsed below
    CORS_ORIGINS: str = "http://localhost:3000"

    # Allowed file extensions
    ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg,webp"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS whether it's comma-separated or JSON array"""
        v = self.CORS_ORIGINS.strip()
        if v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                pass
        return [o.strip() for o in v.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def get_template_path(self, filename: str = "invoice_template.docx") -> str:
        return os.path.join(self.TEMPLATE_DIR, filename)


settings = Settings()
