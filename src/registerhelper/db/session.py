from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from registerhelper.settings import settings

_url = settings.database_url

# make sure data/ exists.
if _url.startswith("sqlite:///"):
    Path(_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(_url)

if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    """with get_session() as s: ...  commits on success, rolls back on error."""
    with SessionLocal() as session, session.begin():
        yield session
