from typing import Any

from registerhelper.adapters.platform_adapter import PlatformAdapter, register_platform
from registerhelper.models import Term


@register_platform("banner9")
class Banner9Adapter(PlatformAdapter):
    def list_terms(self) -> list[Term]:
        raise NotImplementedError

    def fetch_sections(self, term: str) -> list[dict[str, Any]]:
        raise NotImplementedError
