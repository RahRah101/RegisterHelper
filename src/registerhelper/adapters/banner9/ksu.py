"""Kennesaw State University: Banner 9 plus KSU's own codes."""

from registerhelper.adapters.banner9.banner9 import Banner9Adapter, BannerCodes
from registerhelper.adapters.platform_adapter import register_platform
from registerhelper.models import Modality


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
            # unmapped, not sure yet: KSU Center, GA Film Academy, Off Campus,
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
