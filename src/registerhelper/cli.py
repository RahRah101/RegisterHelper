import logging
from collections import Counter
from typing import Annotated

import typer

from registerhelper.adapters import load_plugins
from registerhelper.adapters.platform_adapter import PlatformAdapter, get_platform
from registerhelper.config import load_school
from registerhelper.models import Section
from registerhelper.raw_data import load_raw, save_raw

app = typer.Typer(no_args_is_help=True, help="RegisterHelper")


def _adapter(school: str) -> PlatformAdapter:
    cfg = load_school(school)
    return get_platform(cfg.platform)(base_url=cfg.base_url)


@app.callback()
def main(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show progress logs")
    ] = False,
) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )
    load_plugins()


@app.command()
def terms(school: str) -> None:
    """List the school's terms."""
    for t in _adapter(school).list_terms():
        flag = "  (view only)" if t.view_only else ""
        typer.echo(f"{t.code}  {t.description}{flag}")


@app.command()
def fetch(school: str, term: Annotated[str, typer.Option("--term", "-t")]) -> None:
    """Download every section of a term, save the raw snapshot, normalize it."""
    adapter = _adapter(school)
    raw = adapter.fetch_sections(term)
    path = save_raw(school, term, raw)
    typer.echo(f"saved {len(raw)} raw sections -> {path}")
    _summary(adapter.normalize_sections(raw), len(raw))


@app.command()
def normalize(school: str, term: Annotated[str, typer.Option("--term", "-t")]) -> None:
    """Re-normalize a saved snapshot. Offline, no requests to the school."""
    fetched_at, raw = load_raw(school, term)
    typer.echo(f"snapshot fetched {fetched_at:%Y-%m-%d %H:%M} UTC")
    _summary(_adapter(school).normalize_sections(raw), len(raw))


def _summary(sections: list[Section], raw_count: int) -> None:
    typer.echo(
        f"normalized {len(sections)} sections ({raw_count - len(sections)} skipped)"
    )
    for subject, n in Counter(s.course.subject for s in sections).most_common(10):
        typer.echo(f"  {subject}: {n}")
