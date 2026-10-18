from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, model_validator

type JSON = str | int | float | bool | None | list[JSON] | dict[str, JSON]
type RawSection = dict[str, JSON]


class Weekday(StrEnum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


# TODO: It would be more elegant to have the modality in the Meeting object. That way async/sync is not needed as it is implicitely expressed in the Meeting object(if there is None in the list of days, and it's ONLINE, then it's async, for example). For now the current model is easier to parse/handle.
class Modality(StrEnum):
    IN_PERSON = "in_person"
    HYBRID = "hybrid"
    ONLINE_SYNC = "online_sync"
    ONLINE_ASYNC = "online_async"
    UNKNOWN = "unknown"


class Term(BaseModel):
    code: str
    description: str
    view_only: bool


class CourseRef(BaseModel):
    subject: str
    number: str


class InstructorRef(BaseModel):
    name: str
    external_id: str


class Meeting(BaseModel):
    days: set[Weekday]  # empty means no specific day(usually async online)
    start: time | None
    end: time | None
    start_date: date
    end_date: date
    location: str | None

    @model_validator(mode="after")
    def check_times(self) -> "Meeting":
        if (self.start is None) != (self.end is None):
            raise ValueError("start and end must both be set or both be None")
        if self.start and self.end and self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class Section(BaseModel):
    term: str
    section_id: str  # for example with Banner it's CRN
    course: CourseRef
    section_number: str
    attribute_codes: set[str]  # raw school codes (like requirement areas etc...)
    credits: float  # some schools use decimal points in their credit hours as crazy as that sounds.
    # TODO: Decimal point credits might cause issues with CP-SAT later. We will probably need to scale by 100 or sumting
    campus: str
    modality: Modality  # refers to in-person/hybrid/online status
    seats: int
    link_group: str | None  # what you must take with it(e.g lab+lecture)
    tags: set[str]  # honors, learning_support, etc...
    instructors: list[InstructorRef]
    meetings: list[Meeting]
    # TODO / TOTHINK : might need restriction, waitlist/capacity/enrolled fields, per-meeting mode
    # TODO: Real link rules
