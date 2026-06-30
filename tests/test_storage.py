import json
import pytest
from pathlib import Path

from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.storage import (
    add_alarm,
    load_alarms,
    remove_alarm,
    save_alarms,
    toggle_alarm,
    update_alarm,
)

ALARM_A = Alarm(
    id="a1",
    label="Morning",
    time="07:00",
    repeat=RepeatMode.DAILY,
    days=(),
    enabled=True,
    created_at="2026-06-30T07:00:00",
)

ALARM_B = Alarm(
    id="b2",
    label="Lunch",
    time="12:00",
    repeat=RepeatMode.ONCE,
    days=(),
    enabled=False,
    created_at="2026-06-30T08:00:00",
)


def test_load_alarms_missing_file(tmp_path):
    result = load_alarms(tmp_path / "nonexistent.json")
    assert result == []


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([ALARM_A, ALARM_B], path)
    loaded = load_alarms(path)
    assert loaded == [ALARM_A, ALARM_B]


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "alarms.json"
    save_alarms([ALARM_A], path)
    assert path.exists()


def test_save_writes_valid_json(tmp_path):
    path = tmp_path / "alarms.json"
    save_alarms([ALARM_A], path)
    data = json.loads(path.read_text())
    assert isinstance(data, list)
    assert data[0]["id"] == "a1"


def test_add_alarm_returns_new_list():
    original = [ALARM_A]
    result = add_alarm(original, ALARM_B)
    assert len(result) == 2
    assert original == [ALARM_A]  # original unchanged


def test_add_alarm_appends_at_end():
    result = add_alarm([ALARM_A], ALARM_B)
    assert result[-1] == ALARM_B


def test_remove_alarm_returns_new_list():
    original = [ALARM_A, ALARM_B]
    result = remove_alarm(original, "a1")
    assert len(result) == 1
    assert result[0] == ALARM_B
    assert len(original) == 2  # original unchanged


def test_remove_alarm_unknown_id():
    result = remove_alarm([ALARM_A], "unknown")
    assert result == [ALARM_A]


def test_toggle_alarm_enables_disabled():
    result = toggle_alarm([ALARM_B], "b2")
    assert result[0].enabled is True


def test_toggle_alarm_disables_enabled():
    result = toggle_alarm([ALARM_A], "a1")
    assert result[0].enabled is False


def test_toggle_alarm_returns_new_list():
    original = [ALARM_A]
    result = toggle_alarm(original, "a1")
    assert result is not original
    assert original[0].enabled is True  # original unchanged


def test_toggle_alarm_unknown_id():
    result = toggle_alarm([ALARM_A], "unknown")
    assert result[0].enabled is True  # unchanged


def test_update_alarm_replaces_correct_alarm():
    from dataclasses import replace
    updated = replace(ALARM_A, label="New label", time="10:00")
    result = update_alarm([ALARM_A, ALARM_B], updated)
    assert result[0].label == "New label"
    assert result[0].time == "10:00"
    assert result[1] == ALARM_B


def test_update_alarm_returns_new_list():
    from dataclasses import replace
    updated = replace(ALARM_A, label="Changed")
    original = [ALARM_A]
    result = update_alarm(original, updated)
    assert result is not original
    assert original[0].label == "Morning"  # original unchanged


def test_update_alarm_unknown_id_leaves_list_unchanged():
    from dataclasses import replace
    ghost = replace(ALARM_A, id="does-not-exist", label="Ghost")
    result = update_alarm([ALARM_A], ghost)
    assert result[0] == ALARM_A
