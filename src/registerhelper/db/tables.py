"""Database tables. Portable on purpose: works on SQLite (local) and Postgres (server).

No Postgres-only types here (JSONB, ARRAY...). Lists use the generic JSON type.
Rows have a `school` column because the DB holds many schools; the pydantic
models don't need it because they're always used in a single school's context.
"""

from datetime import date, time

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


section_instructors = Table(
    "section_instructors",
    Base.metadata,
    Column(
        "section_pk",
        ForeignKey("sections.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "instructor_pk",
        ForeignKey("instructors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class TermRow(Base):
    __tablename__ = "terms"
    __table_args__ = (UniqueConstraint("school", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school: Mapped[str] = mapped_column(String(32))
    code: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(128))
    view_only: Mapped[bool] = mapped_column()


class InstructorRow(Base):
    __tablename__ = "instructors"
    __table_args__ = (UniqueConstraint("school", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(256))

    sections: Mapped[list["SectionRow"]] = relationship(
        secondary=section_instructors, back_populates="instructors"
    )


class SectionRow(Base):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("school", "term", "section_id"),
        Index("ix_sections_course", "school", "term", "subject", "course_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    school: Mapped[str] = mapped_column(String(32))
    term: Mapped[str] = mapped_column(String(16))
    section_id: Mapped[str] = mapped_column(String(32))  # Banner: CRN

    subject: Mapped[str] = mapped_column(String(16))
    course_number: Mapped[str] = mapped_column(String(16))
    section_number: Mapped[str] = mapped_column(String(16))

    credits: Mapped[float] = mapped_column()
    campus: Mapped[str] = mapped_column(String(128))
    modality: Mapped[str] = mapped_column(String(16))  # Modality enum value
    seats: Mapped[int] = mapped_column()
    link_group: Mapped[str | None] = mapped_column(String(32))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    meetings: Mapped[list["MeetingRow"]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
    instructors: Mapped[list[InstructorRow]] = relationship(
        secondary=section_instructors, back_populates="sections"
    )


class MeetingRow(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_pk: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )

    days: Mapped[list[str]] = mapped_column(JSON, default=list)  # Weekday values
    start_time: Mapped[time | None] = mapped_column()
    end_time: Mapped[time | None] = mapped_column()
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date] = mapped_column()
    location: Mapped[str | None] = mapped_column(String(256))

    section: Mapped[SectionRow] = relationship(back_populates="meetings")
