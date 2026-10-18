from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai.ai_extraction import AIExtraction, AIExtractionStatus
from app.models.document.document import Document
from app.models.destination.destination import Destination
from app.models.itinerary.itinerary_day import ItineraryDay
from app.models.itinerary.itinerary_item import ItineraryItem
from app.models.place.place import Place
from app.models.screenshot.screenshot import Screenshot
from app.models.trip.trip import Trip, TripStatus
from app.models.user.user import User


REGION_LABELS = {
    "southeast_asia": "Southeast Asia",
    "east_asia": "Japan & East Asia",
    "europe_uk": "Europe & UK",
    "other": "Other",
}

REGION_COUNTRIES = {
    "southeast_asia": {
        "BN", "ID", "KH", "LA", "MM", "MY", "PH", "SG", "TH", "TL", "VN",
    },
    "east_asia": {
        "CN", "HK", "JP", "KP", "KR", "MO", "MN", "TW",
    },
    "europe_uk": {
        "AD", "AL", "AT", "AX", "BA", "BE", "BG", "BY", "CH", "CY", "CZ",
        "DE", "DK", "EE", "ES", "FI", "FO", "FR", "GB", "GG", "GI", "GR",
        "HR", "HU", "IE", "IM", "IS", "IT", "JE", "LI", "LT", "LU", "LV",
        "MC", "MD", "ME", "MK", "MT", "NL", "NO", "PL", "PT", "RO", "RS",
        "RU", "SE", "SI", "SJ", "SK", "SM", "TR", "UA", "VA", "XK",
    },
}

OCR_CATEGORIES = {
    "flight": "Flight Boarding Passes",
    "hotel": "Hotel & Villa Bookings",
    "transit": "Transit & Island Passes",
    "expense": "Expense Receipts & Split Ledger",
    "other": "Other / Unclassified",
}


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _region_key(country_code: str | None) -> str:
    normalized_code = (country_code or "").strip().upper()
    for region, country_codes in REGION_COUNTRIES.items():
        if normalized_code in country_codes:
            return region
    return "other"


def _ocr_category(
    extraction_type: str,
    extracted_data: dict,
    screenshot_type: object,
    document_type: str | None,
) -> str:
    booking = extracted_data.get("booking")
    booking_kind = booking.get("kind", "") if isinstance(booking, dict) else ""
    source_types = " ".join(
        str(value.value if hasattr(value, "value") else value)
        for value in (extraction_type, screenshot_type, document_type, booking_kind)
        if value
    ).casefold().replace("-", " ").replace("_", " ")

    if any(word in source_types for word in ("flight", "boarding", "airline")):
        return "flight"
    if any(word in source_types for word in ("hotel", "villa", "stay", "accommodation")):
        return "hotel"
    if any(word in source_types for word in ("transit", "transport", "ferry", "ticket", "pass")):
        return "transit"
    if extracted_data.get("expense") is not None or any(
        word in source_types for word in ("expense", "receipt", "ledger")
    ):
        return "expense"
    return "other"


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

    def get_dashboard_analytics(self, now: datetime | None = None) -> dict:
        current_date = (now or datetime.now(timezone.utc)).date()
        end_month = _month_start(current_date)
        start_month = end_month
        for _ in range(6):
            start_month = (start_month - timedelta(days=1)).replace(day=1)
        end_exclusive = _next_month(end_month)
        start_datetime = datetime.combine(start_month, datetime.min.time(), timezone.utc)
        end_datetime = datetime.combine(end_exclusive, datetime.min.time(), timezone.utc)

        months = []
        month_lookup = {}
        month_cursor = start_month
        while month_cursor < end_exclusive:
            month_key = month_cursor.strftime("%Y-%m")
            month_data = {
                "month": month_key,
                "label": month_cursor.strftime("%b"),
                "regions": {
                    region: {"trips": 0, "itinerary_items": 0}
                    for region in REGION_LABELS
                },
            }
            months.append(month_data)
            month_lookup[month_key] = month_data
            month_cursor = _next_month(month_cursor)

        trip_rows = (
            self.db.query(
                func.extract("year", Trip.created_at).label("year"),
                func.extract("month", Trip.created_at).label("month"),
                Destination.country_code,
                Destination.name,
                func.count(Trip.id).label("trip_count"),
            )
            .join(Destination, Trip.destination_id == Destination.id)
            .filter(
                Trip.created_at >= start_datetime,
                Trip.created_at < end_datetime,
            )
            .group_by(
                func.extract("year", Trip.created_at),
                func.extract("month", Trip.created_at),
                Destination.country_code,
                Destination.name,
            )
            .all()
        )

        destination_totals = {}
        for year, month, country_code, destination_name, trip_count in trip_rows:
            month_key = f"{int(year):04d}-{int(month):02d}"
            region = _region_key(country_code)
            if month_key in month_lookup:
                month_lookup[month_key]["regions"][region]["trips"] += int(trip_count)
            destination_totals[destination_name] = (
                destination_totals.get(destination_name, 0) + int(trip_count)
            )

        itinerary_rows = (
            self.db.query(
                func.extract("year", Trip.created_at).label("year"),
                func.extract("month", Trip.created_at).label("month"),
                Destination.country_code,
                func.count(ItineraryItem.id).label("item_count"),
            )
            .join(ItineraryDay, ItineraryDay.trip_id == Trip.id)
            .join(ItineraryItem, ItineraryItem.itinerary_day_id == ItineraryDay.id)
            .join(Destination, Trip.destination_id == Destination.id)
            .filter(
                Trip.created_at >= start_datetime,
                Trip.created_at < end_datetime,
            )
            .group_by(
                func.extract("year", Trip.created_at),
                func.extract("month", Trip.created_at),
                Destination.country_code,
            )
            .all()
        )
        for year, month, country_code, item_count in itinerary_rows:
            month_key = f"{int(year):04d}-{int(month):02d}"
            region = _region_key(country_code)
            if month_key in month_lookup:
                month_lookup[month_key]["regions"][region]["itinerary_items"] += int(item_count)

        extractions = (
            self.db.query(
                AIExtraction.type,
                AIExtraction.extracted_data,
                AIExtraction.requires_human_review,
                Screenshot.type,
                Document.type,
            )
            .outerjoin(Screenshot, AIExtraction.screenshot_id == Screenshot.id)
            .outerjoin(Document, AIExtraction.document_id == Document.id)
            .filter(AIExtraction.status == AIExtractionStatus.COMPLETED)
            .all()
        )
        category_counts = {category: 0 for category in OCR_CATEGORIES}
        human_review_count = 0
        for (
            extraction_type,
            extracted_data,
            requires_human_review,
            screenshot_type,
            document_type,
        ) in extractions:
            category = _ocr_category(
                extraction_type,
                extracted_data or {},
                screenshot_type,
                document_type,
            )
            category_counts[category] += 1
            human_review_count += int(bool(requires_human_review))

        extraction_count = len(extractions)
        categories = [
            {
                "key": key,
                "label": label,
                "count": category_counts[key],
                "percentage": round(category_counts[key] / extraction_count * 100, 1)
                if extraction_count
                else 0,
            }
            for key, label in OCR_CATEGORIES.items()
        ]

        if start_month.year == end_month.year:
            period_label = f"{start_month:%b}–{end_month:%b %Y}"
        else:
            period_label = f"{start_month:%b %Y}–{end_month:%b %Y}"

        return {
            "trip_lifecycle": {
                "period": {
                    "start": start_month.isoformat(),
                    "end": end_month.isoformat(),
                    "label": period_label,
                },
                "regions": [
                    {"key": key, "label": label}
                    for key, label in REGION_LABELS.items()
                ],
                "months": months,
                "top_destinations": [
                    {"name": name, "trips": count}
                    for name, count in sorted(
                        destination_totals.items(),
                        key=lambda item: (-item[1], item[0].casefold()),
                    )[:3]
                ],
            },
            "ocr_model_stats": {
                "total_documents": extraction_count,
                "categories": categories,
                "human_review_count": human_review_count,
                "human_review_rate": round(human_review_count / extraction_count * 100, 1)
                if extraction_count
                else None,
            },
        }
