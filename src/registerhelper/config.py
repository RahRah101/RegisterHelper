from pathlib import Path

import yaml
from pydantic import BaseModel

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "school_configs"


class SchoolConfig(BaseModel):
    """One school's YAML. Extra keys in the file are ignored for now."""

    school: str
    platform: str  # registry name, e.g. "banner9.gsu"
    base_url: str
    timezone: str | None = None


def load_school(name: str) -> SchoolConfig:
    path = _CONFIG_DIR / f"{name}.yaml"
    if not path.exists():
        known = sorted(p.stem for p in _CONFIG_DIR.glob("*.yaml"))
        raise ValueError(f"no config for '{name}', known: {known}")
    return SchoolConfig.model_validate(yaml.safe_load(path.read_text()))
