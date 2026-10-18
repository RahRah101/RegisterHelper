"""Georgia State University: Banner 9 plus GSU's own codes."""

from registerhelper.adapters.banner9.banner9 import Banner9Adapter, BannerCodes
from registerhelper.adapters.platform_adapter import register_platform
from registerhelper.models import Modality


@register_platform("banner9.gsu")
class GsuAdapter(Banner9Adapter):
    codes = BannerCodes(
        modality_attributes={
            "LONL": Modality.ONLINE_ASYNC,
            "SONL": Modality.ONLINE_SYNC,
            "HYB": Modality.HYBRID,
            "LF2F": Modality.IN_PERSON,
        },
        # get_instructionalMethod.json: H "Hybrid 50% or less tech";
        # search_math.json: T "*Tech enhanced classrm inst" (still in person)
        method_modality={
            "H": Modality.HYBRID,
            "P": Modality.HYBRID,  # "Partially Distance +50% tech"
            "T": Modality.IN_PERSON,
            "NULL": Modality.IN_PERSON,  # "No tech used in deliver instru"
            # "NT": TODO verify that, found scraping
        },
        online_methods=frozenset({"E", "F"}),
        # HC "Honors College"; CRLS "Learning Support" (search_math.json);
        # ZNCM/ZLCM no-cost/low-cost materials (USG-wide practice, kept here until
        # a second USG school shows up)
        tag_attributes={
            "HC": "honors",
            "HP": "honors",  # also "Honors College": a second code
            "CRLS": "learning_support",
            "MOWR": "mowr_eligible",  # "Move on When Ready"
            "SI": "supplemental_instruction",
            "SIMU": "simulcast",
            "ZNCM": "no_cost_materials",
            "ZLCM": "low_cost_materials",
        },
        # campus description -> normalized tags
        campus_tags={
            "Dunwoody -Associates courses": frozenset({"perimeter"}),
            "Clarkston -Associates courses": frozenset({"perimeter"}),
            "Decatur -Associates courses": frozenset({"perimeter"}),
            "Newton -Associates courses": frozenset({"perimeter"}),
            "Alpharetta": frozenset(
                {"perimeter"}
            ),  # verify: may also host bachelor's-level sections
            "Atlanta": frozenset({"downtown"}),
            "Online": frozenset({"online"}),
            "Online - Atl US (Mand. Fees)": frozenset({"online"}),
            "Online - Atl GR (Mand. Fees)": frozenset({"online", "graduate"}),
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
        # CRNC "Non Classroom": catches applied music lessons and similar
        individualized_attributes=frozenset({"CRNC"}),
        individualized_campuses=frozenset({"Off Campus-Tech & USG Fee only"}),
    )
