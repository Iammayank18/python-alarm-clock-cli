from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.storage import (
    DEFAULT_STORAGE,
    add_alarm,
    load_alarms,
    remove_alarm,
    save_alarms,
    toggle_alarm,
    update_alarm,
)

app = typer.Typer(help="Alarm CLI — manage and run alarms from your terminal.")
console = Console()

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _validate_time(value: str) -> str:
    if not _TIME_RE.match(value):
        raise typer.BadParameter("Time must be in HH:MM 24-hour format (e.g. 09:30).")
    return value


@app.command()
def add(
    label: str = typer.Argument(..., help="Alarm label"),
    time: str = typer.Option(..., "--time", "-t", help="Alarm time in HH:MM format"),
    repeat: RepeatMode = typer.Option(RepeatMode.ONCE, "--repeat", "-r", help="Repeat mode"),
    days: Optional[str] = typer.Option(
        None, "--days", "-d", help="Comma-separated weekday indices 0-6 (used with --repeat custom)"
    ),
) -> None:
    """Add a new alarm."""
    _validate_time(time)

    custom_days: tuple[int, ...] = ()
    if repeat == RepeatMode.CUSTOM:
        if not days:
            console.print("[red]--days is required when --repeat is custom.[/red]")
            raise typer.Exit(1)
        try:
            custom_days = tuple(int(d.strip()) for d in days.split(","))
        except ValueError:
            console.print("[red]--days must be comma-separated integers (e.g. 0,2,4).[/red]")
            raise typer.Exit(1)

    alarm = Alarm(
        id=str(uuid.uuid4()),
        label=label,
        time=time,
        repeat=repeat,
        days=custom_days,
        enabled=True,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    alarms = load_alarms()
    updated = add_alarm(alarms, alarm)
    save_alarms(updated)
    console.print(f"[green]Alarm added:[/green] {label} at {time} ({repeat.value})")


@app.command("list")
def list_alarms() -> None:
    """List all alarms."""
    alarms = load_alarms()
    if not alarms:
        console.print("[yellow]No alarms set. Use 'alarm add' to create one.[/yellow]")
        return

    table = Table(title="Alarms", show_lines=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Label", style="bold")
    table.add_column("Time", justify="center")
    table.add_column("Repeat", justify="center")
    table.add_column("Status", justify="center")

    for a in alarms:
        status = "[green]enabled[/green]" if a.enabled else "[red]disabled[/red]"
        short_id = a.id[:8]
        table.add_row(short_id, a.label, a.time, a.repeat.value, status)

    console.print(table)
    console.print(f"[dim]Total: {len(alarms)} alarm(s)[/dim]")


@app.command()
def delete(
    alarm_id: str = typer.Argument(..., help="Alarm ID (or prefix) to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete an alarm by ID."""
    alarms = load_alarms()
    match = _find_alarm(alarms, alarm_id)
    if match is None:
        console.print(f"[red]No alarm found with ID starting with '{alarm_id}'.[/red]")
        raise typer.Exit(1)

    if not yes:
        confirmed = typer.confirm(f"Delete alarm '{match.label}' ({match.time})?")
        if not confirmed:
            console.print("Aborted.")
            return

    updated = remove_alarm(alarms, match.id)
    save_alarms(updated)
    console.print(f"[green]Deleted:[/green] {match.label}")


@app.command()
def edit(
    alarm_id: str = typer.Argument(..., help="Alarm ID (or prefix) to edit"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="New label"),
    time: Optional[str] = typer.Option(None, "--time", "-t", help="New time in HH:MM format"),
    repeat: Optional[RepeatMode] = typer.Option(None, "--repeat", "-r", help="New repeat mode"),
    days: Optional[str] = typer.Option(None, "--days", "-d", help="New comma-separated weekday indices 0-6"),
) -> None:
    """Edit an existing alarm's label, time, or repeat schedule."""
    alarms = load_alarms()
    match = _find_alarm(alarms, alarm_id)
    if match is None:
        console.print(f"[red]No alarm found with ID starting with '{alarm_id}'.[/red]")
        raise typer.Exit(1)

    if not any([label, time, repeat, days]):
        console.print("[yellow]Nothing to update. Provide at least one of --label, --time, --repeat, --days.[/yellow]")
        return

    new_time = match.time
    if time is not None:
        _validate_time(time)
        new_time = time

    new_repeat = repeat if repeat is not None else match.repeat
    new_days = match.days

    if days is not None:
        try:
            new_days = tuple(int(d.strip()) for d in days.split(","))
        except ValueError:
            console.print("[red]--days must be comma-separated integers (e.g. 0,2,4).[/red]")
            raise typer.Exit(1)

    if new_repeat == RepeatMode.CUSTOM and not new_days:
        console.print("[red]--days is required when --repeat is custom.[/red]")
        raise typer.Exit(1)

    from dataclasses import replace as dc_replace
    updated = dc_replace(
        match,
        label=label if label is not None else match.label,
        time=new_time,
        repeat=new_repeat,
        days=new_days,
    )
    save_alarms(update_alarm(alarms, updated))
    console.print(f"[green]Updated:[/green] {updated.label} at {updated.time} ({updated.repeat.value})")


@app.command()
def enable(alarm_id: str = typer.Argument(..., help="Alarm ID (or prefix) to enable")) -> None:
    """Enable an alarm."""
    _set_enabled(alarm_id, target=True)


@app.command()
def disable(alarm_id: str = typer.Argument(..., help="Alarm ID (or prefix) to disable")) -> None:
    """Disable an alarm."""
    _set_enabled(alarm_id, target=False)


@app.command()
def start() -> None:
    """Start the alarm daemon (blocking). Press Ctrl+C to stop."""
    from alarm_cli.scheduler import start_scheduler
    start_scheduler()


# ── helpers ──────────────────────────────────────────────────────────────────

def _find_alarm(alarms: list[Alarm], prefix: str) -> Alarm | None:
    matches = [a for a in alarms if a.id.startswith(prefix)]
    return matches[0] if len(matches) == 1 else None


def _set_enabled(alarm_id: str, *, target: bool) -> None:
    alarms = load_alarms()
    match = _find_alarm(alarms, alarm_id)
    if match is None:
        console.print(f"[red]No alarm found with ID starting with '{alarm_id}'.[/red]")
        raise typer.Exit(1)

    if match.enabled == target:
        state = "already enabled" if target else "already disabled"
        console.print(f"[yellow]Alarm '{match.label}' is {state}.[/yellow]")
        return

    updated = toggle_alarm(alarms, match.id)
    save_alarms(updated)
    action = "Enabled" if target else "Disabled"
    console.print(f"[green]{action}:[/green] {match.label}")
