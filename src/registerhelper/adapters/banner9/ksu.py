"""Kennesaw State University: Banner 9 plus KSU's own codes."""

import html
import re
from typing import override

from registerhelper.adapters.banner9.banner9 import (
    Banner9Adapter,
    BannerCodes,
    _BannerSection,  # pyright: ignore[reportPrivateUsage]  (school subclasses in this package share Banner's raw shape)
)
from registerhelper.adapters.platform_adapter import register_platform
from registerhelper.models import Modality

# individualized work listed under regular schedule types at KSU: BIOL 3110L
# "Directed Methods", CHEM 4100 "Directed Applied Research", 9900 "Dissertation
# Development", "Master's Project"... Only for in-person sections with no times:
# online ones never have times, and "Project Management" is a real class.
_INDIVIDUALIZED_TITLE = re.compile(
    r"\b(Directed|Dissertation|Thesis|Project|Portfolio)\b", re.IGNORECASE
)


@register_platform("banner9.ksu")
class KsuAdapter(Banner9Adapter):
    # KSU's search results have sectionAttributes: null, so nothing here is
    # keyed on attribute codes (the get_attribute lookup lists ZLCM/ZNCM, CB*...)
    codes = BannerCodes(
        # get_instructionalMethod.json; E "-DO NOT USE" has 0 sections in 202701
        method_modality={
            "L": Modality.IN_PERSON,  # "Traditional F2F"
            "H3": Modality.HYBRID,  # "Hybrid - 33 percent Online"
            "H": Modality.HYBRID,  # "Hybrid - 50 percent Online"
            "H6": Modality.HYBRID,  # "Hybrid - 66 percent Online"
        },
        # F "Fully at a Distance"; P "Predominately at a Distance" (no section
        # has a building, unlike GSU's P which is hybrid)
        online_methods=frozenset({"F", "P"}),
        # campus description -> normalized tags
        campus_tags={
            "Kennesaw Campus": frozenset({"kennesaw"}),
            "Marietta Campus": frozenset({"marietta"}),
            "KSU Online": frozenset({"online"}),
            "eCampus": frozenset({"online"}),
            # USG eCore: exactly the parts of term G01-G03
            "eCore": frozenset({"online", "ecore"}),
            "Education Study Abroad": frozenset({"study_abroad"}),
            "GA Film Academy": frozenset({"film_academy"}),  # USG program, GFA subject
            # unmapped, not sure yet: KSU Center, Off Campus (all online WebMBA),
            # City Springs Complex, FinTech Academy
        },
        # thesis, internships, directed study...: not regular scheduled classes
        individualized_schedule_types=frozenset(
            {
                "Independent Study (Correspond)",
                "Internship/Practicum",
                "Directed Study (one-to-one)",
                "Dissertation",
                "Thesis",
                "Practice Teaching",
            }
        ),
        # LAB and ONLN are real meetings at KSU, BRKO "Breakout Session" is
        # mostly PHYS recitations with times and rooms
        class_meeting_types=frozenset({"CLAS", "ONLN", "LAB", "BRKO"}),
    )

    @override
    def _is_individualized(
        self, b: _BannerSection, campus: str, attr_codes: set[str]
    ) -> bool:
        if super()._is_individualized(b, campus, attr_codes):
            return True
        title = html.unescape(b.course_title)
        # MUAP applied lessons, timed or not (GSU catches the same with CRNC)
        if title.startswith("Applied Lessons"):
            return True
        untimed = not any(m.meeting_time.begin_time for m in b.meetings_faculty)
        return (
            b.instructional_method == "L"
            and untimed
            and _INDIVIDUALIZED_TITLE.search(title) is not None
        )
