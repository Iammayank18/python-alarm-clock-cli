from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

from rich.console import Console

from alarm_cli.models import Alarm

console = Console()

SOUNDS_DIR = Path(__file__).parent.parent / "sounds"
DEFAULT_SOUND = SOUNDS_DIR / "alarm.wav"


def play_sound(sound_path: Path = DEFAULT_SOUND) -> None:
    """Play a sound file using the platform's built-in player (non-blocking)."""
    if not sound_path.exists():
        return

    if sys.platform == "darwin":
        cmd = ["afplay", str(sound_path)]
    elif sys.platform.startswith("linux"):
        cmd = ["aplay", str(sound_path)]
    else:
        return

    threading.Thread(target=subprocess.run, args=(cmd,), kwargs={"check": False}, daemon=True).start()


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
