from __future__ import annotations

import html
import logging
import re
from datetime import datetime, time
from typing import ClassVar, override

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError
from pydantic.alias_generators import to_camel

from registerhelper.adapters.platform_adapter import PlatformAdapter, register_platform
from registerhelper.models import (
    JSON,
    CourseRef,
    InstructorRef,
    Meeting,
    Modality,
    RawSection,
    Section,
    Term,
    Weekday,
)

log = logging.getLogger(__name__)


@register_platform("banner9")
class Banner9Adapter(PlatformAdapter):
    """Generic Banner 9. Works for any Banner school, but without a school
    subclass, modality comes out UNKNOWN and attributes stay raw ("attr:xxx")."""

    @override
    def list_terms(self) -> list[Term]:
        raise NotImplementedError  # TODO network: classSearch/getTerms -> parse_terms

    @override
    def fetch_sections(self, term: str) -> list[RawSection]:
        raise NotImplementedError  # TODO network: term/search + paginated searchResults

    @override
    def normalize_sections(self, raw: list[RawSection]) -> list[Section]:
        """Bad sections are logged and skipped, so one weird section can't sink a whole term."""
        sections: list[Section] = []
        for item in raw:
            try:
                sections.append(
                    self._parse_section(_BannerSection.model_validate(item))
                )
            except (ValidationError, ValueError) as e:
                log.warning(
                    "skipping section %s: %s", item.get("courseReferenceNumber", "?"), e
                )
        return sections

    # --- school-specific: override in the school's subclass -----------------

    # section attribute code -> modality
    modality_attributes: ClassVar[dict[str, Modality]] = {}
    # instructional method code -> modality
    method_modality: ClassVar[dict[str, Modality]] = {}
    # instructional method codes meaning "online"; sync vs async is decided
    # by whether the meetings have fixed times
    online_methods: ClassVar[frozenset[str]] = frozenset()
    # section attribute code -> normalized tag (unmapped codes become "attr:<code>")
    tag_attributes: ClassVar[dict[str, str]] = {}
    # meeting type codes that are regular class meetings (others, like final
    # exams, are skipped so they don't create fake conflicts). "CLAS" is the
    # code at GSU and Northeastern, but schools can define their own.
    class_meeting_types: ClassVar[frozenset[str]] = frozenset({"CLAS"})
    # US Banner installs use MM/DD/YYYY (GSU, Northeastern); others may not
    date_format: ClassVar[str] = "%m/%d/%Y"

    # --- parsing that uses the school-specific codes above ------------------

    def _parse_section(self, b: _BannerSection) -> Section:
        meetings = [
            self._parse_meeting(m.meeting_time)
            for m in b.meetings_faculty
            if m.meeting_time.meeting_type is None
            or m.meeting_time.meeting_type in self.class_meeting_types
        ]
        codes = {a.code.strip() for a in b.section_attributes}

        credits = b.credit_hours if b.credit_hours is not None else b.credit_hour_low
        if credits is None:
            raise ValueError("no credit hours")

        seats = b.seats_available
        if b.cross_list and b.cross_list_available is not None:
            seats = min(seats, b.cross_list_available)

        return Section(
            term=b.term,
            section_id=b.course_reference_number,
            course=CourseRef(subject=b.subject, number=b.course_number),
            section_number=b.sequence_number,
            credits=credits,
            campus=html.unescape(b.campus_description).strip(),
            modality=self._modality(codes, b.instructional_method, meetings),
            seats=seats,
            link_group=b.link_identifier,
            tags={
                self.tag_attributes.get(c, f"attr:{c.lower()}")
                for c in codes
                if c not in self.modality_attributes
            },
            instructors=[
                InstructorRef(external_id=f.banner_id, name=_clean_name(f.display_name))
                for f in b.faculty
            ],
            meetings=meetings,
        )

    def _parse_meeting(self, m: _BannerMeetingTime) -> Meeting:
        location = None
        if m.building and m.building.upper() != "ONLINE":
            parts = [m.building_description or m.building, m.room]
            location = html.unescape(" ".join(p for p in parts if p)).strip()
        return Meeting(
            days={day for field, day in _DAYS if getattr(m, field)},
            start=_parse_time(m.begin_time),
            end=_parse_time(m.end_time),
            start_date=datetime.strptime(m.start_date, self.date_format).date(),
            end_date=datetime.strptime(m.end_date, self.date_format).date(),
            location=location,
        )

    def _modality(
        self, codes: set[str], method: str | None, meetings: list[Meeting]
    ) -> Modality:
        found = {
            self.modality_attributes[c] for c in codes if c in self.modality_attributes
        }
        if len(found) == 1:
            return found.pop()
        if len(found) > 1:
            return Modality.UNKNOWN  # conflicting attributes... FLAG

        if method is not None:
            if method in self.method_modality:
                return self.method_modality[method]
            if method in self.online_methods:
                has_times = any(m.start is not None for m in meetings)
                return Modality.ONLINE_SYNC if has_times else Modality.ONLINE_ASYNC
        return Modality.UNKNOWN


def parse_terms(raw: list[JSON]) -> list[Term]:
    """Banner-wide: "(View Only)" is how Banner itself marks closed terms."""
    return [
        Term(
            code=t.code,
            description=html.unescape(t.description.replace(_VIEW_ONLY, "")).strip(),
            view_only=_VIEW_ONLY in t.description,
        )
        for t in _terms_adapter.validate_python(raw)
    ]


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    return time(int(value[:2]), int(value[2:]))  # "1130" -> 11:30


def _clean_name(name: str) -> str:
    # "La Corte, Julie (Julie Carmine)  ." -> "La Corte, Julie"
    name = html.unescape(name)
    name = re.sub(r"\s+\.$", "", name)  # drop "(preferred name)"
    name = re.sub(r"[\s.]+$", "", name)  # drop trailing " ."
    return re.sub(r"\s+", " ", name).strip()


# Classes representing Banner's raw shape.
_BANNER = ConfigDict(extra="ignore", alias_generator=to_camel, populate_by_name=True)


class _BannerTerm(BaseModel):
    model_config = _BANNER
    code: str
    description: str


class _BannerMeetingTime(BaseModel):
    model_config = _BANNER
    begin_time: str | None = None  # "1130", None for async online
    end_time: str | None = None
    start_date: str  # "01/11/2027"
    end_date: str
    building: str | None = None
    building_description: str | None = None
    room: str | None = None
    meeting_type: str | None = (
        None  # school-defined code, e.g. "CLAS", "FNEX" (final exam)
    )
    monday: bool = False
    tuesday: bool = False
    wednesday: bool = False
    thursday: bool = False
    friday: bool = False
    saturday: bool = False
    sunday: bool = False


class _BannerMeeting(BaseModel):
    model_config = _BANNER
    meeting_time: _BannerMeetingTime


class _BannerFaculty(BaseModel):
    model_config = _BANNER
    banner_id: str
    display_name: str
    primary_indicator: bool = False


class _BannerAttribute(BaseModel):
    model_config = _BANNER
    code: str
    description: str


class _BannerSection(BaseModel):
    model_config = _BANNER
    term: str
    course_reference_number: str
    subject: str
    course_number: str
    sequence_number: str
    campus_description: str
    credit_hours: float | None = None
    credit_hour_low: float | None = None
    seats_available: int
    cross_list: str | None = None
    cross_list_available: int | None = None
    link_identifier: str | None = None
    instructional_method: str | None = None
    faculty: list[_BannerFaculty] = []
    meetings_faculty: list[_BannerMeeting] = []
    section_attributes: list[_BannerAttribute] = []


# Parsing: raw Banner JSON -> domain layer models. Offline, runs on samples/.
_VIEW_ONLY = "(View Only)"

_DAYS: tuple[tuple[str, Weekday], ...] = (
    ("monday", Weekday.MON),
    ("tuesday", Weekday.TUE),
    ("wednesday", Weekday.WED),
    ("thursday", Weekday.THU),
    ("friday", Weekday.FRI),
    ("saturday", Weekday.SAT),
    ("sunday", Weekday.SUN),
)

_terms_adapter = TypeAdapter(list[_BannerTerm])
