from datetime import datetime, timezone

from app.controllers.common.scoped_resource_controller import ScopedResourceController
from app.models.reminder.reminder import Reminder, ReminderStatus
from app.models.trip.trip import Trip


class ReminderController(ScopedResourceController):
    model = Reminder
    resource_name = "Reminder"

    def validate_create(self, fields: dict) -> None:
        self.require_owned(
            self.db.query(Trip).filter(
                Trip.id == fields["trip_id"],
                Trip.user_id == self.user.id,
            ),
            "Trip",
        )
        if fields.get("status", ReminderStatus.PENDING) == ReminderStatus.COMPLETED:
            fields["completed_at"] = datetime.now(timezone.utc)

    def validate_update(self, resource: Reminder, fields: dict) -> None:
        if "due_date" in fields:
            new_due_date = fields["due_date"]
            old_due_date = resource.due_date
            if old_due_date.tzinfo is None:
                old_due_date = old_due_date.replace(tzinfo=timezone.utc)
            if new_due_date != old_due_date:
                fields["email_sent_at"] = None
                fields["email_claimed_at"] = None

        if "status" in fields:
            new_status = fields["status"]
            if (
                new_status == ReminderStatus.COMPLETED
                and resource.status != ReminderStatus.COMPLETED
            ):
                fields["completed_at"] = datetime.now(timezone.utc)
            elif (
                new_status != ReminderStatus.COMPLETED
                and resource.status == ReminderStatus.COMPLETED
            ):
                fields["completed_at"] = None
