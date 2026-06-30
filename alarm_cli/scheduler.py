from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from rich.console import Console
from rich.table import Table

from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.storage import DEFAULT_STORAGE, load_alarms, remove_alarm, save_alarms

console = Console()


def build_trigger(alarm: Alarm) -> CronTrigger | DateTrigger:
    hour, minute = alarm.time.split(":")

    if alarm.repeat == RepeatMode.ONCE:
        now = datetime.now()
        fire_at = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        if fire_at <= now:
            fire_at += timedelta(days=1)
        return DateTrigger(run_date=fire_at)

    day_map = {
        RepeatMode.DAILY: "*",
        RepeatMode.WEEKDAYS: "mon-fri",
        RepeatMode.WEEKENDS: "sat,sun",
    }

    if alarm.repeat in day_map:
        return CronTrigger(hour=int(hour), minute=int(minute), day_of_week=day_map[alarm.repeat])

    if alarm.repeat == RepeatMode.CUSTOM:
        if not alarm.days:
            raise ValueError(f"Alarm '{alarm.label}' has repeat=CUSTOM but no days set.")
        day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        dow = ",".join(day_names[d] for d in alarm.days)
        return CronTrigger(hour=int(hour), minute=int(minute), day_of_week=dow)

    raise ValueError(f"Unknown RepeatMode: {alarm.repeat}")


def _make_job(alarm: Alarm, storage_path: Path, snooze_minutes: int):
    def job():
        from alarm_cli.notifier import notify
        choice = notify(alarm, snooze_minutes)
        if choice == "s":
            _snooze(alarm, snooze_minutes, storage_path)
        elif alarm.repeat == RepeatMode.ONCE:
            alarms = load_alarms(storage_path)
            save_alarms(remove_alarm(alarms, alarm.id), storage_path)
            console.print(f"[dim]Alarm '{alarm.label}' removed (one-time).[/dim]")
    return job


def _snooze(alarm: Alarm, minutes: int, storage_path: Path) -> None:
    from apscheduler.schedulers.background import BackgroundScheduler
    snooze_time = datetime.now() + timedelta(minutes=minutes)
    bg = BackgroundScheduler()
    bg.add_job(_make_job(alarm, storage_path, minutes), DateTrigger(run_date=snooze_time))
    bg.start()
    console.print(f"[yellow]Snoozed '{alarm.label}' until {snooze_time.strftime('%H:%M')}.[/yellow]")


def sync_alarms(
    scheduler: BlockingScheduler,
    storage_path: Path,
    snooze_minutes: int = 5,
    *,
    silent: bool = False,
) -> int:
    """
    Reconcile scheduler jobs against the alarms file.
    Removes stale jobs, adds new ones. Returns count of active jobs.
    """
    alarms = load_alarms(storage_path)
    desired = {a.id: a for a in alarms if a.enabled}
    current_ids = {job.id for job in scheduler.get_jobs()}

    removed = current_ids - desired.keys()
    added = desired.keys() - current_ids

    for job_id in removed:
        scheduler.remove_job(job_id)

    for alarm_id in added:
        alarm = desired[alarm_id]
        trigger = build_trigger(alarm)
        scheduler.add_job(_make_job(alarm, storage_path, snooze_minutes), trigger, id=alarm_id)

    if not silent and (removed or added):
        for job_id in removed:
            console.print(f"[dim]  – removed: {job_id[:8]}[/dim]")
        for alarm_id in added:
            a = desired[alarm_id]
            console.print(f"[green]  + {a.label}[/green] at {a.time} ({a.repeat.value})")

    return len(desired)


def _watch_file(
    scheduler: BlockingScheduler,
    storage_path: Path,
    snooze_minutes: int,
    stop_event: threading.Event,
    poll_interval: int = 10,
) -> None:
    """Poll the alarms file and sync scheduler whenever the file changes."""
    last_mtime: float = storage_path.stat().st_mtime if storage_path.exists() else 0.0

    while not stop_event.wait(poll_interval):
        current_mtime = storage_path.stat().st_mtime if storage_path.exists() else 0.0
        if current_mtime != last_mtime:
            last_mtime = current_mtime
            count = sync_alarms(scheduler, storage_path, snooze_minutes)
            console.print(f"[dim]Alarms reloaded — {count} active[/dim]")


# ── public entry point ────────────────────────────────────────────────────────

def register_alarms(
    scheduler: BlockingScheduler,
    alarms: list[Alarm],
    storage_path: Path,
    snooze_minutes: int = 5,
) -> int:
    count = 0
    for alarm in alarms:
        if not alarm.enabled:
            continue
        trigger = build_trigger(alarm)
        scheduler.add_job(_make_job(alarm, storage_path, snooze_minutes), trigger, id=alarm.id)
        count += 1
    return count


def start_scheduler(storage_path: Path = DEFAULT_STORAGE, snooze_minutes: int = 5) -> None:
    scheduler = BlockingScheduler()
    stop_event = threading.Event()

    # Initial sync
    count = sync_alarms(scheduler, storage_path, snooze_minutes, silent=True)
    _print_startup_banner(load_alarms(storage_path), count)

    # File watcher runs in background; detects any alarm add/edit/delete
    watcher = threading.Thread(
        target=_watch_file,
        args=(scheduler, storage_path, snooze_minutes, stop_event),
        daemon=True,
    )
    watcher.start()

    try:
        scheduler.start()
    except KeyboardInterrupt:
        stop_event.set()
        console.print("\n[dim]Alarm daemon stopped.[/dim]")


def _print_startup_banner(alarms: list[Alarm], active_count: int) -> None:
    console.print("\n[bold green]Alarm daemon started[/bold green] — Press Ctrl+C to stop")
    console.print("[dim]New alarms are picked up automatically within 10 seconds.[/dim]\n")
    if not alarms:
        console.print("[yellow]No alarms yet. Run 'alarm add' in another terminal.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Label")
    table.add_column("Time", justify="center")
    table.add_column("Repeat", justify="center")
    table.add_column("Status", justify="center")
    for a in alarms:
        status = "[green]active[/green]" if a.enabled else "[dim]disabled[/dim]"
        table.add_row(a.label, a.time, a.repeat.value, status)
    console.print(table)
    console.print(f"[dim]{active_count} alarm(s) scheduled[/dim]\n")
