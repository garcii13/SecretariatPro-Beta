from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Filesystem locations used by the SecretariatPro engine."""

    base_dir: Path

    @classmethod
    def from_file(cls, file_path: str | Path) -> "AppPaths":
        return cls(Path(file_path).resolve().parent)

    @property
    def data_file(self) -> Path:
        return self.base_dir / "data.json"

    @property
    def app_settings_file(self) -> Path:
        return self.base_dir / "app_settings.json"

    @property
    def account_settings_file(self) -> Path:
        return self.base_dir / "account_settings.json"

    @property
    def ocr_config_file(self) -> Path:
        return self.base_dir / "ocr_config.json"

    @property
    def subscription_access_file(self) -> Path:
        return self.base_dir / "subscription_access.json"

    @property
    def scores_dir(self) -> Path:
        return self.base_dir / "scores"
