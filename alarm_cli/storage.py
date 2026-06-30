from __future__ import annotations

import json
from pathlib import Path

from alarm_cli.models import Alarm, alarm_from_dict, alarm_to_dict

DEFAULT_STORAGE = Path.home() / ".alarm_cli" / "alarms.json"


def load_alarms(path: Path = DEFAULT_STORAGE) -> list[Alarm]:
    if not path.exists():
        return []
    with path.open() as f:
        return [alarm_from_dict(d) for d in json.load(f)]


def save_alarms(alarms: list[Alarm], path: Path = DEFAULT_STORAGE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump([alarm_to_dict(a) for a in alarms], f, indent=2)


def add_alarm(alarms: list[Alarm], alarm: Alarm) -> list[Alarm]:
    return [*alarms, alarm]


def remove_alarm(alarms: list[Alarm], alarm_id: str) -> list[Alarm]:
    return [a for a in alarms if a.id != alarm_id]


def toggle_alarm(alarms: list[Alarm], alarm_id: str) -> list[Alarm]:
    from dataclasses import replace
    return [
        replace(a, enabled=not a.enabled) if a.id == alarm_id else a
        for a in alarms
    ]


def update_alarm(alarms: list[Alarm], updated: Alarm) -> list[Alarm]:
    return [updated if a.id == updated.id else a for a in alarms]
