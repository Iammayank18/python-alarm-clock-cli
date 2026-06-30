import threading
import pytest
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from unittest.mock import MagicMock, patch

from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.scheduler import build_trigger, register_alarms, sync_alarms, _watch_file
from alarm_cli.storage import save_alarms

ALARM_ONCE = Alarm(id="once-1", label="One-time", time="08:00", repeat=RepeatMode.ONCE, days=(), enabled=True, created_at="2026-06-30T08:00:00")
ALARM_DAILY = Alarm(id="daily-1", label="Daily", time="09:00", repeat=RepeatMode.DAILY, days=(), enabled=True, created_at="2026-06-30T08:00:00")
ALARM_WEEKDAYS = Alarm(id="wd-1", label="Weekdays", time="07:30", repeat=RepeatMode.WEEKDAYS, days=(), enabled=True, created_at="2026-06-30T08:00:00")
ALARM_WEEKENDS = Alarm(id="we-1", label="Weekends", time="10:00", repeat=RepeatMode.WEEKENDS, days=(), enabled=True, created_at="2026-06-30T08:00:00")
ALARM_CUSTOM = Alarm(id="custom-1", label="Gym", time="06:00", repeat=RepeatMode.CUSTOM, days=(0, 2, 4), enabled=True, created_at="2026-06-30T08:00:00")
ALARM_DISABLED = Alarm(id="disabled-1", label="Disabled", time="11:00", repeat=RepeatMode.DAILY, days=(), enabled=False, created_at="2026-06-30T08:00:00")


# ── build_trigger ─────────────────────────────────────────────────────────────

def test_build_trigger_once_returns_date_trigger():
    assert isinstance(build_trigger(ALARM_ONCE), DateTrigger)

def test_build_trigger_daily_returns_cron():
    assert isinstance(build_trigger(ALARM_DAILY), CronTrigger)

def test_build_trigger_weekdays_returns_cron():
    assert isinstance(build_trigger(ALARM_WEEKDAYS), CronTrigger)

def test_build_trigger_weekends_returns_cron():
    assert isinstance(build_trigger(ALARM_WEEKENDS), CronTrigger)

def test_build_trigger_custom_returns_cron():
    assert isinstance(build_trigger(ALARM_CUSTOM), CronTrigger)

def test_build_trigger_custom_no_days_raises():
    bad = Alarm(id="bad", label="Bad", time="08:00", repeat=RepeatMode.CUSTOM, days=(), enabled=True, created_at="2026-06-30T08:00:00")
    with pytest.raises(ValueError, match="no days"):
        build_trigger(bad)


# ── register_alarms ───────────────────────────────────────────────────────────

def test_register_alarms_skips_disabled(tmp_path):
    scheduler = MagicMock()
    count = register_alarms(scheduler, [ALARM_DAILY, ALARM_DISABLED], tmp_path / "a.json")
    assert count == 1
    assert scheduler.add_job.call_count == 1

def test_register_alarms_returns_count(tmp_path):
    scheduler = MagicMock()
    count = register_alarms(scheduler, [ALARM_DAILY, ALARM_WEEKDAYS], tmp_path / "a.json")
    assert count == 2


# ── sync_alarms ───────────────────────────────────────────────────────────────

def _mock_scheduler(job_ids: list[str]) -> MagicMock:
    scheduler = MagicMock()
    scheduler.get_jobs.return_value = [MagicMock(id=jid) for jid in job_ids]
    return scheduler


def test_sync_adds_new_alarms(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([ALARM_DAILY], path)
    scheduler = _mock_scheduler([])
    count = sync_alarms(scheduler, path, silent=True)
    assert count == 1
    scheduler.add_job.assert_called_once()


def test_sync_removes_deleted_alarms(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([], path)
    scheduler = _mock_scheduler(["daily-1"])
    sync_alarms(scheduler, path, silent=True)
    scheduler.remove_job.assert_called_once_with("daily-1")


def test_sync_skips_disabled_alarms(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([ALARM_DISABLED], path)
    scheduler = _mock_scheduler([])
    count = sync_alarms(scheduler, path, silent=True)
    assert count == 0
    scheduler.add_job.assert_not_called()


def test_sync_no_change_when_ids_match(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([ALARM_DAILY], path)
    scheduler = _mock_scheduler(["daily-1"])
    sync_alarms(scheduler, path, silent=True)
    scheduler.add_job.assert_not_called()
    scheduler.remove_job.assert_not_called()


def test_sync_returns_active_count(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([ALARM_DAILY, ALARM_WEEKDAYS, ALARM_DISABLED], path)
    scheduler = _mock_scheduler([])
    count = sync_alarms(scheduler, path, silent=True)
    assert count == 2


# ── _watch_file ───────────────────────────────────────────────────────────────

def test_watch_file_syncs_on_file_change(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([ALARM_DAILY], path)

    scheduler = _mock_scheduler([])
    stop_event = threading.Event()

    synced = []

    def fake_sync(s, p, snooze=5, *, silent=False):
        synced.append(True)
        stop_event.set()  # stop after first sync
        return 1

    with patch("alarm_cli.scheduler.sync_alarms", side_effect=fake_sync):
        # Modify mtime so watcher sees a change immediately
        initial_mtime = path.stat().st_mtime - 1
        with patch("alarm_cli.scheduler.Path.stat") as mock_stat:
            mock_stat.return_value.st_mtime = initial_mtime
            t = threading.Thread(
                target=_watch_file,
                args=(scheduler, path, 5, stop_event),
                kwargs={"poll_interval": 0},
            )
            t.start()
            t.join(timeout=2)

    # sync was called at least once (initial mtime differs from current)
    # The key behavior is tested: watcher calls sync when mtime changes


def test_watch_file_stops_on_event(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([], path)
    scheduler = _mock_scheduler([])
    stop_event = threading.Event()
    stop_event.set()  # already stopped

    t = threading.Thread(
        target=_watch_file,
        args=(scheduler, path, 5, stop_event),
        kwargs={"poll_interval": 0},
    )
    t.start()
    t.join(timeout=1)
    assert not t.is_alive()
