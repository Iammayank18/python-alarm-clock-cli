import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.notifier import _afplay_available, play_sound, send_notification, prompt_snooze_or_dismiss

ALARM = Alarm(
    id="n1",
    label="Wake up",
    time="07:00",
    repeat=RepeatMode.DAILY,
    days=(),
    enabled=True,
    created_at="2026-06-30T07:00:00",
)


def test_play_sound_skips_when_afplay_unavailable():
    with patch("alarm_cli.notifier.shutil.which", return_value=None):
        with patch("alarm_cli.notifier.subprocess.run") as mock_run:
            play_sound()
            mock_run.assert_not_called()


def test_play_sound_calls_afplay_on_macos():
    with patch("alarm_cli.notifier._afplay_available", return_value=True), \
         patch("alarm_cli.notifier.subprocess.run") as mock_run:
        play_sound()
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "afplay"
        assert "Ping.aiff" in str(cmd[1])


def test_send_notification_macos_calls_osascript():
    with patch("alarm_cli.notifier.sys") as mock_sys, \
         patch("alarm_cli.notifier.subprocess.run") as mock_run:
        mock_sys.platform = "darwin"
        send_notification(ALARM)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "osascript"
        assert "Wake up" in cmd[2]
        assert "Glass" in cmd[2]


def test_send_notification_linux_calls_notify_send():
    with patch("alarm_cli.notifier.sys") as mock_sys, \
         patch("alarm_cli.notifier.subprocess.run") as mock_run:
        # MagicMock != "darwin" by default, so the darwin branch is skipped.
        # Configure startswith so the linux branch is taken.
        mock_sys.platform.startswith.return_value = True
        send_notification(ALARM)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "notify-send"


def test_send_notification_does_not_raise_on_subprocess_error():
    with patch("alarm_cli.notifier.sys") as mock_sys, \
         patch("alarm_cli.notifier.subprocess.run", side_effect=Exception("no display")):
        mock_sys.platform = "darwin"
        send_notification(ALARM)  # should not raise


def test_prompt_returns_snooze(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "s")
    result = prompt_snooze_or_dismiss(ALARM)
    assert result == "s"


def test_prompt_returns_dismiss(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "d")
    result = prompt_snooze_or_dismiss(ALARM)
    assert result == "d"


def test_prompt_case_insensitive(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "D")
    result = prompt_snooze_or_dismiss(ALARM)
    assert result == "d"


def test_prompt_retries_on_invalid_input(monkeypatch):
    responses = iter(["x", "q", "d"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    result = prompt_snooze_or_dismiss(ALARM)
    assert result == "d"
