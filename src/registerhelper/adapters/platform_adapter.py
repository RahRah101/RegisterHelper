from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from registerhelper.models import Section, Term

type RawSection = dict[str, Any]


class PlatformAdapter(ABC):
    @abstractmethod
    def list_terms(self) -> list[Term]: ...
    @abstractmethod
    def fetch_sections(self, term: str) -> list[RawSection]: ...
    @abstractmethod
    def normalize(self, raw: list[RawSection]) -> list[Section]: ...


A = TypeVar("A", bound=PlatformAdapter)
_PLATFORMS: dict[str, type[PlatformAdapter]] = {}


def register_platform(name: str) -> Callable[[type[A]], type[A]]:
    def deco(cls: type[A]) -> type[A]:
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
