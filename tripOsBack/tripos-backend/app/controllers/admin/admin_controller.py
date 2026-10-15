from sqlalchemy.orm import Session

from app.models.ai.ai_extraction import AIExtraction
from app.models.destination.destination import Destination
from app.models.place.place import Place
from app.models.trip.trip import Trip, TripStatus
from app.models.user.user import User


class AdminController:
    def __init__(self, db: Session):
        self.db = db

    def count_users(self) -> int:
        return self.db.query(User).count()

    def get_dashboard(self) -> dict[str, dict[str, int | float]]:
        active_trip_statuses = (
            TripStatus.PLANNING,
            TripStatus.UPCOMING,
            TripStatus.ONGOING,
        )
        return {
            "statistics": {
                "total_registered_travelers": self.db.query(User).count(),
                "active_trips_managed": self.db.query(Trip)
                .filter(Trip.status.in_(active_trip_statuses))
                .count(),
                "ai_screenshot_parse_jobs": self.db.query(AIExtraction)
                .filter(AIExtraction.screenshot_id.is_not(None))
                .count(),
                "destination_catalog": self.db.query(Destination).count(),
                "place_catalog": self.db.query(Place).count(),
            }
        }
