from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RepeatMode(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Alarm:
    id: str
    label: str
    time: str          # "HH:MM" 24-hour
    repeat: RepeatMode
    days: tuple[int, ...]  # 0=Mon … 6=Sun; used only when repeat=CUSTOM
    enabled: bool
    created_at: str    # ISO 8601


def alarm_to_dict(alarm: Alarm) -> dict:
    return {
        "id": alarm.id,
        "label": alarm.label,
        "time": alarm.time,
        "repeat": alarm.repeat.value,
        "days": list(alarm.days),
        "enabled": alarm.enabled,
        "created_at": alarm.created_at,
    }


def alarm_from_dict(data: dict) -> Alarm:
    return Alarm(
        id=data["id"],
        label=data["label"],
        time=data["time"],
        repeat=RepeatMode(data["repeat"]),
        days=tuple(data.get("days", [])),
        enabled=data["enabled"],
        created_at=data["created_at"],
    )
