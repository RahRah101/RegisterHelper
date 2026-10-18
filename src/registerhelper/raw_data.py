from datetime import datetime
from pathlib import Path

from registerhelper.models import RawSection
from registerhelper.settings import settings


def _path(school: str, term: str) -> Path:
    return settings.data_dir / "raw" / school / f"{term}.json"


def save_raw(school: str, term: str, sections: list[RawSection]) -> Path: ...


def load_raw(school: str, term: str) -> tuple[datetime, list[RawSection]]: ...
