from __future__ import annotations

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
    alarms = load_alarms(storage_path)
    enabled = [a for a in alarms if a.enabled]

    scheduler = BlockingScheduler()
    count = register_alarms(scheduler, enabled, storage_path, snooze_minutes)

    _print_startup_banner(enabled)

    if count == 0:
        console.print("[yellow]No enabled alarms. Add one with 'alarm add'.[/yellow]")
        return

    try:
        scheduler.start()
    except KeyboardInterrupt:
        console.print("\n[dim]Alarm daemon stopped.[/dim]")


def _print_startup_banner(alarms: list[Alarm]) -> None:
    console.print("\n[bold green]Alarm daemon started[/bold green] — Press Ctrl+C to stop\n")
    if not alarms:
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Label")
    table.add_column("Time", justify="center")
    table.add_column("Repeat", justify="center")
    for a in alarms:
        table.add_row(a.label, a.time, a.repeat.value)
    console.print(table)
    console.print()
