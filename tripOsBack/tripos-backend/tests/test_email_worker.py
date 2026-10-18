import asyncio

import pytest

from app.services import email_worker


def test_email_worker_fails_clearly_without_gmail_settings(monkeypatch):
    monkeypatch.setattr(
        email_worker,
        "reminder_email_is_configured",
        lambda: False,
    )
    monkeypatch.setattr(
        email_worker,
        "missing_reminder_email_settings",
        lambda: ("GMAIL_REFRESH_TOKEN",),
    )

    with pytest.raises(RuntimeError, match="GMAIL_REFRESH_TOKEN"):
        asyncio.run(email_worker.run_email_worker())


def test_email_worker_processes_due_reminders_and_notifications(monkeypatch):
    calls = []

    async def run_in_thread(function):
        calls.append(function)
        return function()

    async def stop_after_cycle(_delay):
        raise RuntimeError("stop test worker after one delivery cycle")

    monkeypatch.setattr(
        email_worker,
        "reminder_email_is_configured",
        lambda: True,
    )
    monkeypatch.setattr(
        email_worker,
        "process_due_reminder_emails",
        lambda: 1,
    )
    monkeypatch.setattr(
        email_worker,
        "process_due_notification_emails",
        lambda: 2,
    )
    monkeypatch.setattr(email_worker.asyncio, "to_thread", run_in_thread)
    monkeypatch.setattr(email_worker.asyncio, "sleep", stop_after_cycle)

    with pytest.raises(RuntimeError, match="stop test worker"):
        asyncio.run(email_worker.run_email_worker())

    assert calls == [
        email_worker.process_due_reminder_emails,
        email_worker.process_due_notification_emails,
    ]
