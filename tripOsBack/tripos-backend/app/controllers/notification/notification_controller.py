from datetime import datetime, timezone

from fastapi import HTTPException

from app.controllers.common.scoped_resource_controller import ScopedResourceController
from app.models.notification.notification import Notification
from app.models.reminder.reminder import Reminder
from app.models.trip.trip import Trip


class NotificationController(ScopedResourceController):
    model = Notification
    resource_name = "Notification"

    def validate_create(self, fields: dict) -> None:
        trip_id = fields.get("trip_id")
        reminder_id = fields.get("reminder_id")

        if trip_id is not None:
            self.require_owned(
                self.db.query(Trip).filter(
                    Trip.id == trip_id,
                    Trip.user_id == self.user.id,
                ),
                "Trip",
            )

        if reminder_id is not None:
            reminder = self.db.query(Reminder).filter(
                Reminder.id == reminder_id,
                Reminder.user_id == self.user.id,
            ).first()
            if reminder is None:
                raise HTTPException(status_code=404, detail="Reminder not found")
            if trip_id is not None and reminder.trip_id != trip_id:
                raise HTTPException(
                    status_code=422,
                    detail="Reminder does not belong to the specified trip",
                )

    def validate_update(self, resource: Notification, fields: dict) -> None:
        if "due_date" not in fields:
            return

        new_due_date = fields["due_date"]
        old_due_date = resource.due_date
        if old_due_date is not None and old_due_date.tzinfo is None:
            old_due_date = old_due_date.replace(tzinfo=timezone.utc)
        if new_due_date is not None and new_due_date.tzinfo is None:
            new_due_date = new_due_date.replace(tzinfo=timezone.utc)
        if new_due_date != old_due_date:
            fields["email_sent_at"] = None
            fields["email_claimed_at"] = None
