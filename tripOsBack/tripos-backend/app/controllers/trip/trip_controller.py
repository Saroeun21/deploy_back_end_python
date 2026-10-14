from fastapi import HTTPException

from app.controllers.common.scoped_resource_controller import ScopedResourceController
from app.models.destination.destination import Destination
from app.models.trip.trip import Trip


class TripController(ScopedResourceController):
    model = Trip
    resource_name = "Trip"

    def validate_create(self, fields: dict) -> None:
        self._validate_destination(fields.get("destination_id"))
        model_fields = set(Trip.__table__.columns.keys())
        extra_fields = {
            key: fields.pop(key)
            for key in list(fields)
            if key not in model_fields
        }
        fields["data"] = {**fields.get("data", {}), **extra_fields}

    def validate_update(self, resource: Trip, fields: dict) -> None:
        if "destination_id" in fields:
            self._validate_destination(fields["destination_id"])

    def _validate_destination(self, destination_id: int | None) -> None:
        if self.db.get(Destination, destination_id) is None:
            raise HTTPException(status_code=404, detail="Destination not found")
