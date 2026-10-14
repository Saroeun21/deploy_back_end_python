from fastapi import HTTPException
from sqlalchemy.orm import joinedload

from app.controllers.common.scoped_resource_controller import ScopedResourceController
from app.models.place.place import Place
from app.models.saved_place.saved_place import SavedPlace


class SavedPlaceController(ScopedResourceController):
    model = SavedPlace
    resource_name = "Saved place"

    def query_owned(self):
        return (
            self.db.query(self.model)
            .options(joinedload(self.model.place))
            .filter(self.owner_filter())
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )

    def validate_create(self, fields: dict) -> None:
        place = self.db.query(Place).filter(Place.id == fields["place_id"]).first()
        if place is None:
            raise HTTPException(status_code=404, detail="Place not found")

        existing = self.db.query(SavedPlace).filter(
            SavedPlace.user_id == self.user.id,
            SavedPlace.place_id == place.id,
        ).first()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Place already saved")
