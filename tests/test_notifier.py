import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from alarm_cli.models import Alarm, RepeatMode
from alarm_cli.notifier import play_sound, send_notification, prompt_snooze_or_dismiss

ALARM = Alarm(
    id="n1",
    label="Wake up",
    time="07:00",
    repeat=RepeatMode.DAILY,
    days=(),
    enabled=True,
    created_at="2026-06-30T07:00:00",
)


def test_play_sound_skips_missing_file(tmp_path):
    missing = tmp_path / "nope.wav"
    # should not raise even though file is absent
    play_sound(missing)


def test_play_sound_calls_afplay_on_macos(tmp_path):
    sound = tmp_path / "alarm.wav"
    sound.write_bytes(b"RIFF")  # fake wav

    with patch("alarm_cli.notifier.sys") as mock_sys, \
         patch("alarm_cli.notifier.subprocess.run") as mock_run, \
         patch("alarm_cli.notifier.threading.Thread") as mock_thread:
        mock_sys.platform = "darwin"
        instance = MagicMock()
        mock_thread.return_value = instance
        play_sound(sound)
        mock_thread.assert_called_once()
        instance.start.assert_called_once()


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
