import json
from datetime import UTC, datetime
from pathlib import Path

from registerhelper.models import RawSection
from registerhelper.settings import settings


def _path(school: str, term: str) -> Path:
    return settings.data_dir / "raw" / school / f"{term}.json"


def save_raw(school: str, term: str, sections: list[RawSection]) -> Path:
    path = _path(school, term)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(UTC).isoformat(),
        "sections": sections,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload))
    tmp.replace(path)
    return path


def load_raw(school: str, term: str) -> tuple[datetime, list[RawSection]]:
    payload = json.loads(_path(school, term).read_text())
    return datetime.fromisoformat(payload["fetched_at"]), payload["sections"]
