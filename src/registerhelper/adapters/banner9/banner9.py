from __future__ import annotations

import html
import logging
import random
import re
import string
from datetime import datetime, time
from time import sleep
from typing import ClassVar, override

import httpx
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


class BannerCodes(BaseModel):
    """A school's own Banner codes. Everything here is school-defined."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # section attribute code -> modality
    modality_attributes: dict[str, Modality] = {}
    # instructional method code -> modality
    method_modality: dict[str, Modality] = {}
    # instructional method codes meaning "online"; sync vs async is decided
    # by whether the meetings have fixed times
    online_methods: frozenset[str] = frozenset()
    # section attribute code -> normalized tag (raw codes are kept in attribute_codes)
    tag_attributes: dict[str, str] = {}
    # campus description -> normalized tags (e.g. "perimeter", "online")
    campus_tags: dict[str, frozenset[str]] = {}
    # a section matching ANY of these three gets the "individualized" tag
    # (thesis, internships, directed study...: not regular scheduled classes)
    individualized_schedule_types: frozenset[str] = frozenset()
    individualized_attributes: frozenset[str] = frozenset()
    individualized_campuses: frozenset[str] = frozenset()
    # meeting type codes that are regular class meetings (others, like final
    # exams, are skipped so they don't create fake conflicts). "CLAS" is the
    # code at GSU and Northeastern, but schools can define their own.
    class_meeting_types: frozenset[str] = frozenset({"CLAS"})
    # US Banner installs use MM/DD/YYYY (GSU, Northeastern); others may not
    date_format: str = "%m/%d/%Y"


@register_platform("banner9")
class Banner9Adapter(PlatformAdapter):
    """Generic Banner 9. Works for any Banner school, but without a school
    subclass, modality comes out UNKNOWN and there are no normalized tags
    (raw attribute codes are still kept in attribute_codes)."""

    codes: ClassVar[BannerCodes] = BannerCodes()

    def __init__(self, base_url: str, delay: float = 1.0) -> None:
        super().__init__(base_url)
        self.delay = delay  # TODO makes this configurable instead of forcing a delay.

    @override
    def list_terms(self) -> list[Term]:
        with self._client() as c:
            raw = self._get(
                c, "/classSearch/getTerms", {"searchTerm": "", "offset": 1, "max": 100}
            )
        if not isinstance(raw, list):
            raise BannerError("getTerms: expected a list")
        return parse_terms(raw)

    @override
    def fetch_sections(self, term: str) -> list[RawSection]:
        sid = _unique_session_id()
        with self._client() as c:
            self._declare_term(c, term, sid)
            sections = self._search_all(c, term, sid)
            if sections:
                log.info("whole term in one search: %d sections", len(sections))
                return sections
            # this Banner won't do an empty search so go subject by subject as a fallback
            log.info("empty search returned nothing, fetching per subject")
            for subject in self._subjects(c, term):
                self._post(
                    c, "/classSearch/resetDataForm"
                )  # Banner remembers the last search
                sections.extend(self._search_all(c, term, sid, subject))
        return sections

    def _declare_term(self, c: httpx.Client, term: str, sid: str) -> None:
        # search is blocked until the session declares which term it's browsing
        self._post(
            c,
            "/term/search",
            params={"mode": "search"},
            data={
                "term": term,
                "studyPath": "",
                "studyPathText": "",
                "startDatepicker": "",
                "endDatepicker": "",
                "uniqueSessionId": sid,
            },
        )

    def _subjects(self, c: httpx.Client, term: str) -> list[str]:
        raw = self._get(
            c,
            "/classSearch/get_subject",
            {"searchTerm": "", "term": term, "offset": 1, "max": 1000},
        )
        return [s.code for s in _lookup_adapter.validate_python(raw)]

    def _search_all(
        self, c: httpx.Client, term: str, sid: str, subject: str | None = None
    ) -> list[RawSection]:
        out: list[RawSection] = []
        offset = 0
        while True:
            params: dict[str, str | int] = {
                "txt_term": term,
                "uniqueSessionId": sid,
                "pageOffset": offset,
                "pageMaxSize": _PAGE_SIZE,
                "sortColumn": "subjectDescription",
                "sortDirection": "asc",
            }
            if subject is not None:
                params["txt_subject"] = subject
            page = _BannerSearchPage.model_validate(
                self._get(c, "/searchResults/searchResults", params)
            )
            if not page.success:
                raise BannerError(
                    "searchResults: success=false (term not declared for this session?)"
                )
            batch = page.data or []
            out.extend(batch)
            offset += _PAGE_SIZE
            if not batch or offset >= page.total_count:
                return out

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=30.0, headers={"User-Agent": "RegisterHelper (course planner)"}
        )

    def _get(self, c: httpx.Client, path: str, params: dict[str, str | int]) -> JSON:
        sleep(self.delay)
        return _json_or_raise(c.get(self.base_url + path, params=params), path)

    def _post(
        self,
        c: httpx.Client,
        path: str,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> None:
        sleep(self.delay)
        r = c.post(self.base_url + path, params=params, data=data)
        if not r.is_success:
            raise BannerError(f"{path}: HTTP {r.status_code}")

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

    # --- parsing that uses the school-specific codes in self.codes -----------

    def _parse_section(self, b: _BannerSection) -> Section:
        meetings = [
            self._parse_meeting(m.meeting_time)
            for m in b.meetings_faculty
            if m.meeting_time.meeting_type is None
            or m.meeting_time.meeting_type in self.codes.class_meeting_types
        ]
        attr_codes = {a.code.strip() for a in b.section_attributes}

        credits = b.credit_hours if b.credit_hours is not None else b.credit_hour_low
        if credits is None:
            raise ValueError("no credit hours")

        seats = b.seats_available
        if b.cross_list and b.cross_list_available is not None:
            seats = min(seats, b.cross_list_available)

        campus = html.unescape(b.campus_description).strip()
        tags = {
            self.codes.tag_attributes[c]
            for c in attr_codes
            if c in self.codes.tag_attributes
        }
        tags |= self.codes.campus_tags.get(campus, frozenset())
        if (
            b.schedule_type_description in self.codes.individualized_schedule_types
            or campus in self.codes.individualized_campuses
            or attr_codes & self.codes.individualized_attributes
        ):
            tags.add("individualized")

        return Section(
            term=b.term,
            section_id=b.course_reference_number,
            course=CourseRef(subject=b.subject, number=b.course_number),
            section_number=b.sequence_number,
            credits=credits,
            campus=campus,
            tags=tags,
            attribute_codes=attr_codes,
            modality=self._modality(attr_codes, b.instructional_method, meetings),
            seats=seats,
            link_group=b.link_identifier,
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
            start_date=datetime.strptime(m.start_date, self.codes.date_format).date(),
            end_date=datetime.strptime(m.end_date, self.codes.date_format).date(),
            location=location,
        )

    def _modality(
        self, codes: set[str], method: str | None, meetings: list[Meeting]
    ) -> Modality:
        found = {
            self.codes.modality_attributes[c]
            for c in codes
            if c in self.codes.modality_attributes
        }
        if len(found) == 1:
            return found.pop()
        if len(found) > 1:
            return Modality.UNKNOWN  # conflicting attributes... FLAG

        if method is not None:
            if method in self.codes.method_modality:
                return self.codes.method_modality[method]
            if method in self.codes.online_methods:
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


class BannerError(Exception):
    """Unfortunately, Banner answered with something other than what we expected...."""


_PAGE_SIZE = 500  # Banner's maximum page size


def _unique_session_id() -> str:
    prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"{prefix}{int(datetime.now().timestamp() * 1000)}"


def _json_or_raise(r: httpx.Response, path: str) -> JSON:
    if r.is_redirect:
        raise BannerError(
            f"{path}: redirected to {r.headers.get('location')} (login wall?)"
        )
    if not r.is_success:
        raise BannerError(f"{path}: HTTP {r.status_code}")
    if "json" not in r.headers.get("content-type", ""):
        raise BannerError(
            f"{path}: expected JSON, got {r.headers.get('content-type')} (error page?)"
        )
    return r.json()  # pyright: ignore[reportAny]


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    return time(int(value[:2]), int(value[2:]))  # "1130" -> 11:30


def _clean_name(name: str) -> str:
    # "La Corte, Julie (Julie Carmine)  ." -> "La Corte, Julie"
    name = html.unescape(name)
    name = re.sub(r"\s*\(.*?\)", "", name)  # drop "(preferred name)"
    name = re.sub(r"\s+\.$", "", name)  # drop trailing " ." (keeps "D.")
    return re.sub(r"\s+", " ", name).strip()


# Classes representing Banner's raw shape.
_BANNER = ConfigDict(extra="ignore", alias_generator=to_camel, populate_by_name=True)


class _BannerSearchPage(BaseModel):
    model_config = _BANNER
    success: bool
    total_count: int = 0
    data: list[RawSection] | None = None


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
    schedule_type_description: str | None = None


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
_lookup_adapter = TypeAdapter(list[_BannerTerm])
