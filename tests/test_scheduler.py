import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from unittest.mock import MagicMock, patch

from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.scheduler import build_trigger, register_alarms

ALARM_ONCE = Alarm(
    id="once-1",
    label="One-time",
    time="08:00",
    repeat=RepeatMode.ONCE,
    days=(),
    enabled=True,
    created_at="2026-06-30T08:00:00",
)

ALARM_DAILY = Alarm(
    id="daily-1",
    label="Daily",
    time="09:00",
    repeat=RepeatMode.DAILY,
    days=(),
    enabled=True,
    created_at="2026-06-30T08:00:00",
)

ALARM_WEEKDAYS = Alarm(
    id="wd-1",
    label="Weekdays",
    time="07:30",
    repeat=RepeatMode.WEEKDAYS,
    days=(),
    enabled=True,
    created_at="2026-06-30T08:00:00",
)

ALARM_WEEKENDS = Alarm(
    id="we-1",
    label="Weekends",
    time="10:00",
    repeat=RepeatMode.WEEKENDS,
    days=(),
    enabled=True,
    created_at="2026-06-30T08:00:00",
)

ALARM_CUSTOM = Alarm(
    id="custom-1",
    label="Gym",
    time="06:00",
    repeat=RepeatMode.CUSTOM,
    days=(0, 2, 4),
    enabled=True,
    created_at="2026-06-30T08:00:00",
)

ALARM_DISABLED = Alarm(
    id="disabled-1",
    label="Disabled",
    time="11:00",
    repeat=RepeatMode.DAILY,
    days=(),
    enabled=False,
    created_at="2026-06-30T08:00:00",
)


def test_build_trigger_once_returns_date_trigger():
    trigger = build_trigger(ALARM_ONCE)
    assert isinstance(trigger, DateTrigger)


def test_build_trigger_daily_returns_cron():
    trigger = build_trigger(ALARM_DAILY)
    assert isinstance(trigger, CronTrigger)


def test_build_trigger_weekdays_returns_cron():
    trigger = build_trigger(ALARM_WEEKDAYS)
    assert isinstance(trigger, CronTrigger)


def test_build_trigger_weekends_returns_cron():
    trigger = build_trigger(ALARM_WEEKENDS)
    assert isinstance(trigger, CronTrigger)


def test_build_trigger_custom_returns_cron():
    trigger = build_trigger(ALARM_CUSTOM)
    assert isinstance(trigger, CronTrigger)


def test_build_trigger_custom_no_days_raises():
    bad = Alarm(
        id="bad",
        label="Bad",
        time="08:00",
        repeat=RepeatMode.CUSTOM,
        days=(),
        enabled=True,
        created_at="2026-06-30T08:00:00",
    )
    with pytest.raises(ValueError, match="no days"):
        build_trigger(bad)


def test_register_alarms_skips_disabled(tmp_path):
    scheduler = MagicMock()
    count = register_alarms(scheduler, [ALARM_DAILY, ALARM_DISABLED], tmp_path / "a.json")
    assert count == 1
    assert scheduler.add_job.call_count == 1


def test_register_alarms_returns_count(tmp_path):
    scheduler = MagicMock()
    count = register_alarms(scheduler, [ALARM_DAILY, ALARM_WEEKDAYS], tmp_path / "a.json")
    assert count == 2
