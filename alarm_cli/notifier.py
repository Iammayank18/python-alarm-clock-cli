from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from alarm_cli.models import Alarm

console = Console()

MACOS_SOUNDS = "/System/Library/Sounds"
DEFAULT_SOUND = Path(MACOS_SOUNDS) / "Ping.aiff"


def _afplay_available() -> bool:
    return sys.platform == "darwin" and shutil.which("afplay") is not None


def play_sound() -> None:
    if not _afplay_available():
        return
    subprocess.run(["afplay", str(DEFAULT_SOUND)], capture_output=True)


def send_notification(alarm: Alarm) -> None:
    """Send a desktop notification using platform-native tools (no third-party deps)."""
    try:
        if sys.platform == "darwin":
            script = (
                f'display notification "{alarm.label}" '
                f'with title "Alarm" subtitle "{alarm.time}" '
                f'sound name "Glass"'
            )
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
        elif sys.platform.startswith("linux"):
            subprocess.run(
                ["notify-send", "Alarm", f"{alarm.label} — {alarm.time}"],
                check=False,
                timeout=5,
            )
    except Exception:
        pass  # notification is best-effort


def prompt_snooze_or_dismiss(alarm: Alarm, snooze_minutes: int = 5) -> str:
    """
    Prompt the user to snooze or dismiss.
    Returns 's' for snooze, 'd' for dismiss.
    """
    console.print(f"\n[bold yellow]ALARM[/bold yellow] {alarm.label} ({alarm.time})")
    while True:
        choice = input(f"  [S]nooze {snooze_minutes}min / [D]ismiss: ").strip().lower()
        if choice in ("s", "d"):
            return choice
        console.print("  Please enter S or D.")


def notify(alarm: Alarm, snooze_minutes: int = 5) -> str:
    """Fire alarm: play sound, notify, prompt user. Returns 's' or 'd'."""
    play_sound()
    send_notification(alarm)
    return prompt_snooze_or_dismiss(alarm, snooze_minutes)
