"""Command line: `warnbot run` and `warnbot status`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import db, pipeline
from .job import JobContext, ntfy_notifier, run_job
from .store import Store

HELP = "Posts new California WARN Act layoff notices to Mastodon."

app = typer.Typer(help=HELP, no_args_is_help=True)


@app.command()
def run(
    dry_run: Annotated[
        bool, typer.Option(help="Show what would be posted; change nothing.")
    ] = False,
    max_items: Annotated[
        int, typer.Option("--max", min=1, help="Most notices to post in this run.")
    ] = 20,
    report_url: Annotated[
        str | None, typer.Option(help="Report URL instead of finding it on the EDD page.")
    ] = None,
    file: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="Local .xlsx report.")
    ] = None,
) -> None:
    """Do one run: fetch the report, record new notices, post them."""
    if report_url and file:
        raise typer.BadParameter("use --report-url or --file, not both")

    conn = db.connect()

    def work(ctx: JobContext) -> str:
        summary = pipeline.run(
            conn,
            max_posts=ctx.max_items,
            dry_run=ctx.dry_run,
            report_url=report_url,
            report_file=file,
            log=ctx.log,
        )
        return pipeline.describe(summary)

    try:
        ok = run_job(
            "run",
            work,
            conn=conn,
            lock_path=Path("data/run.lock"),
            dry_run=dry_run,
            max_items=max_items,
            notify=ntfy_notifier(),
            log=typer.echo,
        )
    finally:
        conn.close()
    if not ok:
        raise typer.Exit(1)


@app.command()
def status(limit: int = 10) -> None:
    """Show recent runs."""
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        notices = Store(conn).counts()
    finally:
        conn.close()
    typer.echo("notices: " + (", ".join(f"{k} {v}" for k, v in sorted(notices.items())) or "none"))
    for r in rows:
        state = "running" if r["ok"] is None else ("ok" if r["ok"] else "FAILED")
        dry = " (dry run)" if r["dry_run"] else ""
        typer.echo(f"{r['started_at']}  {r['job']}  {state}{dry}  {r['detail'] or ''}")
