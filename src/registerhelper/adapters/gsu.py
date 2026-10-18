"""Georgia State University: Banner 9 plus GSU's own codes."""

from typing import ClassVar

from registerhelper.adapters.banner9 import Banner9Adapter
from registerhelper.adapters.platform_adapter import register_platform
from registerhelper.models import Modality


@register_platform("banner9.gsu")
class GsuAdapter(Banner9Adapter):
    modality_attributes: ClassVar[dict[str, Modality]] = {
        "LONL": Modality.ONLINE_ASYNC,
        "SONL": Modality.ONLINE_SYNC,
        "HYB": Modality.HYBRID,
        "LF2F": Modality.IN_PERSON,
    }
    # get_instructionalMethod.json: H "Hybrid 50% or less tech";
    # search_math.json: T "*Tech enhanced classrm inst" (still in person)
    method_modality: ClassVar[dict[str, Modality]] = {
        "H": Modality.HYBRID,
        "T": Modality.IN_PERSON,
    }

    online_methods: ClassVar[frozenset[str]] = frozenset({"E", "F"})

    # HC "Honors College"; CRLS "Learning Support" (search_math.json);
    # ZNCM/ZLCM no-cost/low-cost materials (USG-wide practice, kept here until
    # a second USG school shows up)
    tag_attributes: ClassVar[dict[str, str]] = {
        "HC": "honors",
        "CRLS": "learning_support",
        "ZNCM": "no_cost_materials",
        "ZLCM": "low_cost_materials",
    }
