# Alarm CLI

A clean, cross-platform alarm clock application for the terminal — no database, no web server, just Python.

## Features

- **Add alarms** with a label, time, and repeat schedule (once, daily, weekdays, weekends, or custom days)
- **List alarms** in a formatted table with ID, label, time, repeat mode, and status
- **Edit alarms** — update label, time, repeat mode, or custom days without recreating
- **Delete alarms** with an optional confirmation prompt
- **Enable / disable alarms** without deleting them
- **Sound + desktop notification** when an alarm fires
- **Snooze or dismiss** from the terminal prompt when an alarm triggers
- **Persistent storage** via `~/.alarm_cli/alarms.json` — no database required

---

## Installation

```bash
# Clone and set up a virtual environment
git clone <repo-url> alarm-cli
cd alarm-cli
python3 -m venv .venv
source .venv/bin/activate

# Install the package and its dependencies
pip install -e .
```

---

## Usage

### Add an alarm

```bash
# One-time alarm
alarm add "Team meeting" --time 14:00

# Daily alarm
alarm add "Morning standup" --time 09:30 --repeat daily

# Weekdays only
alarm add "Wake up" --time 07:00 --repeat weekdays

# Weekends only
alarm add "Sleep in" --time 09:00 --repeat weekends

# Custom days (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
alarm add "Gym" --time 06:30 --repeat custom --days 0,2,4
```

### List alarms

```bash
alarm list
```

Output:

```
          Alarms
┌──────────┬───────────────┬───────┬──────────┬──────────┐
│ ID       │ Label         │ Time  │ Repeat   │ Status   │
├──────────┼───────────────┼───────┼──────────┼──────────┤
│ a1b2c3d4 │ Morning       │ 07:00 │ daily    │ enabled  │
│ e5f6g7h8 │ Team meeting  │ 14:00 │ once     │ disabled │
└──────────┴───────────────┴───────┴──────────┴──────────┘
Total: 2 alarm(s)
```

### Edit an alarm

Use the first 8 characters of the alarm ID (shown in `alarm list`).

```bash
# Change the label
alarm edit a1b2c3d4 --label "Wake up early"

# Change the time
alarm edit a1b2c3d4 --time 06:30

# Change the repeat schedule
alarm edit a1b2c3d4 --repeat weekdays

# Change multiple fields at once
alarm edit a1b2c3d4 --label "Gym" --time 06:00 --repeat custom --days 0,2,4
```

### Delete an alarm

```bash
# Prompts for confirmation
alarm delete a1b2c3d4

# Skip confirmation
alarm delete a1b2c3d4 --yes
```

### Enable / disable an alarm

```bash
alarm enable a1b2c3d4
alarm disable a1b2c3d4
```

### Start the daemon

Runs a blocking background process that watches for alarms and fires them.

```bash
alarm start
```

When an alarm fires:
- A sound plays (via `afplay` on macOS)
- A desktop notification appears
- A terminal prompt asks: **[S]nooze / [D]ismiss**
  - **S** — snooze for 5 minutes (re-triggers automatically)
  - **D** — dismiss the alarm

Press `Ctrl+C` to stop the daemon.

---

## Repeat Modes

| Mode | Description |
|---|---|
| `once` | Fires once at the next occurrence of the given time (default) |
| `daily` | Fires every day at the given time |
| `weekdays` | Fires Monday through Friday |
| `weekends` | Fires Saturday and Sunday |
| `custom` | Fires on specific days — requires `--days 0,2,4` (0=Mon … 6=Sun) |

---

## Command Reference

| Command | Description |
|---|---|
| `alarm add "<label>" --time HH:MM [--repeat MODE] [--days 0,2,4]` | Add a new alarm |
| `alarm list` | List all alarms |
| `alarm edit <id> [--label] [--time] [--repeat] [--days]` | Edit an existing alarm |
| `alarm delete <id> [--yes]` | Delete an alarm |
| `alarm enable <id>` | Enable a disabled alarm |
| `alarm disable <id>` | Disable an alarm without deleting it |
| `alarm start` | Start the blocking alarm daemon |

---

## Project Structure

```
alarm-cli/
├── alarm_cli/
│   ├── __main__.py        # Entry point: python -m alarm_cli
│   ├── cli.py             # All CLI commands (typer)
│   ├── models.py          # Alarm dataclass + RepeatMode enum
│   ├── storage.py         # JSON file read/write (immutable pattern)
│   ├── scheduler.py       # APScheduler daemon
│   └── notifier.py        # Sound + desktop notification + snooze prompt
├── sounds/
│   └── alarm.wav          # Default alarm sound
├── tests/                 # 64 tests, 80%+ coverage
├── docs/
│   ├── architecture.md
│   └── implementation-plan.md
└── pyproject.toml
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
pytest --cov=alarm_cli --cov-report=term-missing
```

---

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | Component design, data model, and tech stack |
| [Implementation Plan](docs/implementation-plan.md) | Phased build plan with TDD workflow |
