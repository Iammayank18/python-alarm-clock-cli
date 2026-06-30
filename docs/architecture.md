# Architecture

## Overview

Alarm CLI is structured as a single Python package (`alarm_cli`) with clearly separated concerns:
CLI → Storage → Models → Scheduler → Notifier. There is no web layer and no database — alarms
are persisted in a JSON file at `~/.alarm_cli/alarms.json`.

---

## Tech Stack

| Concern | Library | Reason |
|---|---|---|
| CLI interface | `typer` | Auto-generates `--help`, cleaner than argparse |
| Terminal UI | `rich` | Tables, colors, formatted output |
| Scheduling | `APScheduler` | Battle-tested cron + interval job support |
| Sound playback | `playsound` | Simple cross-platform audio |
| Desktop notifications | `plyer` | Cross-platform system notification API |
| Persistence | JSON file | No DB needed, human-readable, zero dependencies |

---

## Project Structure

```
alarm-cli/
├── alarm_cli/
│   ├── __init__.py
│   ├── __main__.py       # Entry point: python -m alarm_cli
│   ├── cli.py            # Typer app — all CLI commands
│   ├── models.py         # Alarm dataclass + RepeatMode enum (immutable)
│   ├── storage.py        # Read/write ~/.alarm_cli/alarms.json
│   ├── scheduler.py      # APScheduler daemon logic
│   └── notifier.py       # Sound playback + desktop notification
├── sounds/
│   └── alarm.wav         # Default alarm sound
├── tests/
│   ├── test_models.py
│   ├── test_storage.py
│   ├── test_scheduler.py
│   └── test_cli.py
├── docs/
│   ├── architecture.md
│   └── implementation-plan.md
└── pyproject.toml
```

---

## Component Responsibilities

```
CLI (cli.py)
  │  Commands: add / list / delete / enable / disable / start
  │
  ▼
Storage (storage.py)
  │  load_alarms()   — reads JSON file, returns list of Alarm
  │  save_alarms()   — writes list of Alarm to JSON file
  │  add_alarm()     — returns new list with alarm appended (no mutation)
  │  remove_alarm()  — returns new list with alarm removed
  │  toggle_alarm()  — returns new list with enabled flag flipped
  │
  ▼
Models (models.py)
  │  Alarm: frozen dataclass — immutable, serialized to/from dict
  │  RepeatMode: Enum — ONCE | DAILY | WEEKDAYS | WEEKENDS | CUSTOM
  │
  ├──► Scheduler (scheduler.py)
  │       Runs as a blocking process via `alarm start`
  │       Reads alarms from storage on startup
  │       Maps RepeatMode → APScheduler CronTrigger
  │       Calls notifier when a job fires
  │       Removes ONCE alarms after they fire
  │
  └──► Notifier (notifier.py)
          Plays sounds/alarm.wav via playsound
          Sends desktop notification via plyer
          Prompts user: [S]nooze / [D]ismiss
          Snooze re-schedules alarm +N minutes (default 5)
```

---

## Data Model

```python
from dataclasses import dataclass
from enum import Enum

class RepeatMode(Enum):
    ONCE     = "once"
    DAILY    = "daily"
    WEEKDAYS = "weekdays"   # Mon–Fri
    WEEKENDS = "weekends"   # Sat–Sun
    CUSTOM   = "custom"     # specific days via `days` field

@dataclass(frozen=True)
class Alarm:
    id:         str        # uuid4 string
    label:      str        # human-readable name
    time:       str        # "HH:MM" 24-hour format
    repeat:     RepeatMode
    days:       tuple[int] # 0=Mon … 6=Sun; only used when repeat=CUSTOM
    enabled:    bool
    created_at: str        # ISO 8601 timestamp
```

`frozen=True` enforces immutability — nothing modifies an `Alarm` in place.
Updates are done by creating a new `Alarm` instance with the changed field.

---

## Storage Format

File location: `~/.alarm_cli/alarms.json`

```json
[
  {
    "id": "a1b2c3d4-...",
    "label": "Morning standup",
    "time": "09:30",
    "repeat": "daily",
    "days": [],
    "enabled": true,
    "created_at": "2026-06-30T08:00:00"
  }
]
```

---

## Scheduler — RepeatMode to Cron Mapping

| RepeatMode | APScheduler CronTrigger |
|---|---|
| `ONCE` | `date` trigger at next occurrence of `HH:MM` |
| `DAILY` | `cron` — `hour=HH, minute=MM` |
| `WEEKDAYS` | `cron` — `day_of_week=mon-fri` |
| `WEEKENDS` | `cron` — `day_of_week=sat,sun` |
| `CUSTOM` | `cron` — `day_of_week=<joined day indices>` |

---

## CLI Commands Reference

```bash
alarm add "<label>" --time HH:MM [--repeat once|daily|weekdays|weekends]
alarm list
alarm delete <alarm-id>
alarm enable <alarm-id>
alarm disable <alarm-id>
alarm start                   # blocking daemon; Ctrl+C to stop
```

---

## Key Design Decisions

### Immutable Data Model
Every storage operation returns a new list — no in-place mutation.
This prevents hidden side effects and makes the storage layer trivially testable.

### File-Per-User Storage
Alarms live in `~/.alarm_cli/alarms.json`. No root permissions required,
no shared state between users, and the file is human-readable and editable.

### Always Read From Disk
The scheduler and CLI always load alarms fresh from the JSON file rather than
caching them in memory. This avoids stale state when both the CLI and daemon
are running at the same time.

### Blocking Daemon
`alarm start` runs a blocking `APScheduler` process rather than registering
system cron jobs. This keeps the application self-contained and cross-platform
without requiring OS-level scheduler access.
