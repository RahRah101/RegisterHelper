from typing import Protocol

class PlatformAdapter(Protocol):
    def list_terms(self) -> list[Term]: ...
    def fetch_sections(self, term: str) -> list[dict]: ...

_PLATFORMS: dict[str, type] = {}

def register_platform(name: str):
    def deco(cls):
        if name in _PLATFORMS:
            raise ValueError(f"platform '{name}' already registered")
        _PLATFORMS[name] = cls
        return cls
    return deco

def get_platform(name: str) -> type:
    try:
        return _PLATFORMS[name]
    except KeyError:
        raise ValueError(f"unknown platform '{name}', known: {sorted(_PLATFORMS)}")
