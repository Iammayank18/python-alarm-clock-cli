# Implementation Plan

All phases follow a TDD workflow: write the test first (RED), implement to pass it (GREEN),
then refactor (IMPROVE). Target 80%+ test coverage across all modules.

---

## Phase 1 — Core Data Layer

**Files:** `alarm_cli/models.py`, `alarm_cli/storage.py`, `tests/test_models.py`, `tests/test_storage.py`

### Goals
- Define the `Alarm` frozen dataclass and `RepeatMode` enum
- Implement file-based persistence with pure, side-effect-free functions

### Tasks

- [ ] Write `test_models.py`
  - Alarm can be created with valid fields
  - Alarm is immutable (assigning a field raises `FrozenInstanceError`)
  - Alarm serializes to/from dict correctly
  - All `RepeatMode` values are valid

- [ ] Implement `models.py`
  - `Alarm` frozen dataclass
  - `RepeatMode` enum
  - `alarm_to_dict()` and `alarm_from_dict()` helpers

- [ ] Write `test_storage.py`
  - `load_alarms()` returns empty list when file does not exist
  - `load_alarms()` returns correct alarms from valid JSON
  - `save_alarms()` writes correct JSON to disk
  - `add_alarm()` returns new list with alarm appended, original unchanged
  - `remove_alarm()` returns new list without the alarm
  - `toggle_alarm()` returns new list with `enabled` flipped

- [ ] Implement `storage.py`
  - `load_alarms(path) -> list[Alarm]`
  - `save_alarms(path, alarms) -> None`
  - `add_alarm(alarms, alarm) -> list[Alarm]`
  - `remove_alarm(alarms, alarm_id) -> list[Alarm]`
  - `toggle_alarm(alarms, alarm_id) -> list[Alarm]`

---

## Phase 2 — CLI Commands

**Files:** `alarm_cli/cli.py`, `alarm_cli/__main__.py`, `tests/test_cli.py`

### Goals
- Wire all user-facing commands to the storage layer
- Display alarms in a `rich` formatted table
- Validate user input before writing to storage

### Tasks

- [ ] Write `test_cli.py` (use Typer's `CliRunner` for integration tests)
  - `alarm add` creates and saves a new alarm
  - `alarm add` with invalid time format shows error and exits non-zero
  - `alarm list` displays all alarms in a table
  - `alarm list` with no alarms shows a friendly empty-state message
  - `alarm delete <id>` removes the alarm and confirms
  - `alarm delete <unknown-id>` shows error
  - `alarm enable <id>` and `alarm disable <id>` toggle correctly

- [ ] Implement `cli.py`
  - `app = typer.Typer()`
  - `add` command — validates `HH:MM` format, creates `Alarm`, calls `add_alarm()`
  - `list` command — loads alarms, renders `rich.Table`
  - `delete` command — prompts confirmation, calls `remove_alarm()`
  - `enable` / `disable` commands — call `toggle_alarm()`
  - `start` command — delegates to `scheduler.py` (Phase 3)

- [ ] Implement `__main__.py`
  - Calls `app()` so `python -m alarm_cli` works

---

## Phase 3 — Scheduler Daemon

**Files:** `alarm_cli/scheduler.py`, `tests/test_scheduler.py`

### Goals
- Load enabled alarms from storage and register them as APScheduler jobs
- Map each `RepeatMode` to the correct trigger type
- Remove `ONCE` alarms from storage after they fire
- Handle `Ctrl+C` gracefully

### Tasks

- [ ] Write `test_scheduler.py`
  - `build_trigger()` returns correct `CronTrigger` for each `RepeatMode`
  - `build_trigger()` raises `ValueError` for unknown `RepeatMode`
  - Only enabled alarms are scheduled
  - `ONCE` alarm is removed from storage after firing
  - `DAILY` alarm remains in storage after firing

- [ ] Implement `scheduler.py`
  - `build_trigger(alarm) -> BaseTrigger`
  - `register_alarms(scheduler, alarms, storage_path)` — adds jobs
  - `start(storage_path)` — creates `BlockingScheduler`, registers alarms, starts
  - `KeyboardInterrupt` caught for clean shutdown with a `rich` farewell message

---

## Phase 4 — Notifier

**Files:** `alarm_cli/notifier.py`, `tests/test_notifier.py`

### Goals
- Play alarm sound when triggered
- Send a desktop notification
- Present a terminal prompt: `[S]nooze / [D]ismiss`
- Snooze re-schedules the alarm for +N minutes

### Tasks

- [ ] Write `test_notifier.py` (mock `playsound`, `plyer.notification`, and `input`)
  - Sound is played when `notify()` is called
  - Desktop notification is sent with the alarm label
  - Choosing `S` (snooze) schedules a one-time job N minutes from now
  - Choosing `D` (dismiss) does nothing further
  - Invalid input re-prompts the user

- [ ] Implement `notifier.py`
  - `notify(alarm, scheduler, snooze_minutes=5)`
  - Plays `sounds/alarm.wav` in a background thread (non-blocking)
  - Sends desktop notification via `plyer.notification.notify()`
  - Loops on `input()` until valid choice is entered

---

## Phase 5 — Configuration & Polish

**Files:** `alarm_cli/config.py`, `~/.alarm_cli/config.json`

### Goals
- Allow user-level configuration without touching code
- Improve error messages and terminal output
- Ensure clean behavior at edge cases

### Tasks

- [ ] Implement `config.py`
  - `load_config(path) -> dict` with defaults:
    - `snooze_minutes: 5`
    - `sound_file: "<package>/sounds/alarm.wav"`
    - `storage_file: "~/.alarm_cli/alarms.json"`

- [ ] Polish `cli.py`
  - All error states print via `rich.print("[red]...[/red]")` 
  - `alarm list` shows a count summary footer
  - `alarm start` prints a startup banner with scheduled alarm count

- [ ] Polish `scheduler.py`
  - On start, print a `rich` table of all scheduled alarms
  - On `Ctrl+C`, print shutdown message cleanly

- [ ] Add `pyproject.toml`
  - Package entry point: `alarm = alarm_cli.cli:app`
  - Dependencies: `typer`, `rich`, `APScheduler`, `playsound`, `plyer`

---

## Test Coverage Targets

| Module | Target |
|---|---|
| `models.py` | 100% |
| `storage.py` | 100% |
| `cli.py` | 90% |
| `scheduler.py` | 85% |
| `notifier.py` | 80% |

---

## Dependency Summary

```toml
[project]
dependencies = [
  "typer>=0.12",
  "rich>=13",
  "APScheduler>=3.10",
  "playsound>=1.3",
  "plyer>=2.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-cov",
]
```
