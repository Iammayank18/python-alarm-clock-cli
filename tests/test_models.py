import pytest
from dataclasses import FrozenInstanceError

from alarm_cli.models import Alarm, RepeatMode, alarm_from_dict, alarm_to_dict

SAMPLE = Alarm(
    id="abc-123",
    label="Wake up",
    time="07:00",
    repeat=RepeatMode.DAILY,
    days=(),
    enabled=True,
    created_at="2026-06-30T07:00:00",
)


def test_alarm_creation():
    assert SAMPLE.id == "abc-123"
    assert SAMPLE.label == "Wake up"
    assert SAMPLE.time == "07:00"
    assert SAMPLE.repeat == RepeatMode.DAILY
    assert SAMPLE.enabled is True


def test_alarm_is_immutable():
    with pytest.raises(FrozenInstanceError):
        SAMPLE.label = "changed"  # type: ignore[misc]


def test_alarm_to_dict():
    d = alarm_to_dict(SAMPLE)
    assert d["id"] == "abc-123"
    assert d["repeat"] == "daily"
    assert d["days"] == []
    assert d["enabled"] is True


def test_alarm_from_dict_roundtrip():
    d = alarm_to_dict(SAMPLE)
    restored = alarm_from_dict(d)
    assert restored == SAMPLE


def test_alarm_from_dict_with_custom_days():
    d = {
        "id": "xyz",
        "label": "Gym",
        "time": "06:30",
        "repeat": "custom",
        "days": [0, 2, 4],
        "enabled": True,
        "created_at": "2026-06-30T06:30:00",
    }
    alarm = alarm_from_dict(d)
    assert alarm.repeat == RepeatMode.CUSTOM
    assert alarm.days == (0, 2, 4)


def test_repeat_mode_values():
    assert RepeatMode("once") == RepeatMode.ONCE
    assert RepeatMode("daily") == RepeatMode.DAILY
    assert RepeatMode("weekdays") == RepeatMode.WEEKDAYS
    assert RepeatMode("weekends") == RepeatMode.WEEKENDS
    assert RepeatMode("custom") == RepeatMode.CUSTOM


def test_repeat_mode_invalid():
    with pytest.raises(ValueError):
        RepeatMode("monthly")
