import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from alarm_cli.cli import app
from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.storage import save_alarms

runner = CliRunner()

ALARM_A = Alarm(
    id="aaaa1111-0000-0000-0000-000000000000",
    label="Morning",
    time="07:00",
    repeat=RepeatMode.DAILY,
    days=(),
    enabled=True,
    created_at="2026-06-30T07:00:00",
)

ALARM_B = Alarm(
    id="bbbb2222-0000-0000-0000-000000000000",
    label="Lunch",
    time="12:00",
    repeat=RepeatMode.ONCE,
    days=(),
    enabled=False,
    created_at="2026-06-30T08:00:00",
)


@pytest.fixture(autouse=True)
def storage_path(tmp_path, monkeypatch):
    """Redirect all storage operations to a temp file."""
    path = tmp_path / "alarms.json"
    monkeypatch.setattr("alarm_cli.cli.load_alarms", lambda: _load(path))
    monkeypatch.setattr("alarm_cli.cli.save_alarms", lambda alarms: _save(alarms, path))
    return path


def _load(path):
    from alarm_cli.storage import load_alarms
    return load_alarms(path)


def _save(alarms, path):
    from alarm_cli.storage import save_alarms
    save_alarms(alarms, path)


# ── add ──────────────────────────────────────────────────────────────────────

def test_add_creates_alarm(storage_path):
    result = runner.invoke(app, ["add", "Wake up", "--time", "08:00"])
    assert result.exit_code == 0
    assert "Wake up" in result.output
    alarms = _load(storage_path)
    assert len(alarms) == 1
    assert alarms[0].label == "Wake up"
    assert alarms[0].time == "08:00"
    assert alarms[0].enabled is True


def test_add_default_repeat_is_once(storage_path):
    runner.invoke(app, ["add", "Meeting", "--time", "14:00"])
    alarms = _load(storage_path)
    assert alarms[0].repeat == RepeatMode.ONCE


def test_add_with_repeat_daily(storage_path):
    runner.invoke(app, ["add", "Standup", "--time", "09:30", "--repeat", "daily"])
    alarms = _load(storage_path)
    assert alarms[0].repeat == RepeatMode.DAILY


def test_add_invalid_time_format(storage_path):
    result = runner.invoke(app, ["add", "Bad", "--time", "9:5"])
    assert result.exit_code != 0
    assert _load(storage_path) == []


def test_add_invalid_time_out_of_range(storage_path):
    result = runner.invoke(app, ["add", "Bad", "--time", "25:00"])
    assert result.exit_code != 0


def test_add_custom_repeat_without_days(storage_path):
    result = runner.invoke(app, ["add", "Gym", "--time", "06:00", "--repeat", "custom"])
    assert result.exit_code != 0
    assert "days" in result.output.lower()


def test_add_custom_repeat_with_days(storage_path):
    result = runner.invoke(
        app, ["add", "Gym", "--time", "06:00", "--repeat", "custom", "--days", "0,2,4"]
    )
    assert result.exit_code == 0
    alarms = _load(storage_path)
    assert alarms[0].days == (0, 2, 4)


# ── list ─────────────────────────────────────────────────────────────────────

def test_list_empty(storage_path):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No alarms" in result.output


def test_list_shows_alarms(storage_path):
    _save([ALARM_A, ALARM_B], storage_path)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Morning" in result.output
    assert "Lunch" in result.output
    assert "07:00" in result.output
    assert "2 alarm(s)" in result.output


def test_list_shows_enabled_status(storage_path):
    _save([ALARM_A, ALARM_B], storage_path)
    result = runner.invoke(app, ["list"])
    assert "enabled" in result.output
    assert "disabled" in result.output


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_removes_alarm(storage_path):
    _save([ALARM_A, ALARM_B], storage_path)
    result = runner.invoke(app, ["delete", "aaaa1111", "--yes"])
    assert result.exit_code == 0
    assert "Morning" in result.output
    alarms = _load(storage_path)
    assert len(alarms) == 1
    assert alarms[0].id == ALARM_B.id


def test_delete_unknown_id(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["delete", "zzzzzzzz", "--yes"])
    assert result.exit_code != 0
    assert "No alarm found" in result.output


def test_delete_prompts_confirmation(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["delete", "aaaa1111"], input="n\n")
    assert result.exit_code == 0
    assert "Aborted" in result.output
    assert len(_load(storage_path)) == 1


# ── enable / disable ──────────────────────────────────────────────────────────

def test_enable_disabled_alarm(storage_path):
    _save([ALARM_B], storage_path)
    result = runner.invoke(app, ["enable", "bbbb2222"])
    assert result.exit_code == 0
    assert _load(storage_path)[0].enabled is True


def test_disable_enabled_alarm(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["disable", "aaaa1111"])
    assert result.exit_code == 0
    assert _load(storage_path)[0].enabled is False


def test_enable_already_enabled(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["enable", "aaaa1111"])
    assert result.exit_code == 0
    assert "already enabled" in result.output


def test_disable_already_disabled(storage_path):
    _save([ALARM_B], storage_path)
    result = runner.invoke(app, ["disable", "bbbb2222"])
    assert result.exit_code == 0
    assert "already disabled" in result.output


def test_enable_unknown_id(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["enable", "zzzzzzzz"])
    assert result.exit_code != 0


# ── edit ──────────────────────────────────────────────────────────────────────

def test_edit_label(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "aaaa1111", "--label", "New name"])
    assert result.exit_code == 0
    assert _load(storage_path)[0].label == "New name"


def test_edit_time(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "aaaa1111", "--time", "10:30"])
    assert result.exit_code == 0
    assert _load(storage_path)[0].time == "10:30"


def test_edit_repeat(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "aaaa1111", "--repeat", "weekdays"])
    assert result.exit_code == 0
    from alarm_cli.models import RepeatMode
    assert _load(storage_path)[0].repeat == RepeatMode.WEEKDAYS


def test_edit_multiple_fields(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "aaaa1111", "--label", "Gym", "--time", "06:00"])
    assert result.exit_code == 0
    alarm = _load(storage_path)[0]
    assert alarm.label == "Gym"
    assert alarm.time == "06:00"


def test_edit_invalid_time(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "aaaa1111", "--time", "99:99"])
    assert result.exit_code != 0
    assert _load(storage_path)[0].time == "07:00"  # unchanged


def test_edit_no_options_warns(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "aaaa1111"])
    assert result.exit_code == 0
    assert "Nothing to update" in result.output


def test_edit_unknown_id(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "zzzzzzzz", "--label", "X"])
    assert result.exit_code != 0
    assert "No alarm found" in result.output


def test_edit_custom_repeat_requires_days(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(app, ["edit", "aaaa1111", "--repeat", "custom"])
    assert result.exit_code != 0


def test_edit_custom_with_days(storage_path):
    _save([ALARM_A], storage_path)
    result = runner.invoke(
        app, ["edit", "aaaa1111", "--repeat", "custom", "--days", "1,3,5"]
    )
    assert result.exit_code == 0
    alarm = _load(storage_path)[0]
    assert alarm.days == (1, 3, 5)
