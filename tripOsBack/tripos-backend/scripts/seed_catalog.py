from __future__ import annotations

import secrets

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Destination, Place, User


CATALOG_EMAIL = "public-catalog@tripos.local"

DESTINATIONS = (
    {
        "name": "Kyoto",
        "country": "Japan",
        "country_code": "JP",
        "description": "Historic temples, quiet gardens, traditional streets, and seasonal cuisine.",
        "image": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1200&q=80",
        "currency": "JPY",
        "language": "Japanese",
        "timezone": "Asia/Tokyo",
        "best_time": "March to May and October to November",
        "average_daily_cost": 17406,
        "average_daily_cost_usd": 110,
        "places": (
            {
                "name": "Fushimi Inari Taisha",
                "category": "temple",
                "description": "A mountainside Shinto shrine known for its thousands of red torii gates.",
                "image": "https://images.unsplash.com/photo-1478436127897-769e1b3f0f36?auto=format&fit=crop&w=1200&q=80",
                "address": "68 Fukakusa Yabunouchicho, Fushimi Ward, Kyoto",
                "latitude": 34.9671,
                "longitude": 135.7727,
                "rating": 4.8,
                "best_time_to_visit": "Early morning",
                "estimated_cost": 0,
                "admission_fee_usd": 0,
                "estimated_visit_cost_usd": 10.74,
                "website": "https://inari.jp/en/",
            },
            {
                "name": "Kiyomizu-dera",
                "category": "temple",
                "description": "A historic hillside temple with a broad wooden terrace overlooking Kyoto.",
                "image": "https://images.unsplash.com/photo-1528360983277-13d401cdc186?auto=format&fit=crop&w=1200&q=80",
                "address": "1-294 Kiyomizu, Higashiyama Ward, Kyoto",
                "latitude": 34.9949,
                "longitude": 135.785,
                "rating": 4.7,
                "best_time_to_visit": "Morning",
                "estimated_cost": 500,
                "admission_fee_usd": 3.16,
                "estimated_visit_cost_usd": 13.90,
                "website": "https://www.kiyomizudera.or.jp/en/visit/",
            },
        ),
    },
    {
        "name": "Paris",
        "country": "France",
        "country_code": "FR",
        "description": "Iconic boulevards, world-class museums, historic landmarks, and neighborhood cafes.",
        "image": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=1200&q=80",
        "currency": "EUR",
        "language": "French",
        "timezone": "Europe/Paris",
        "best_time": "April to June and September to October",
        "average_daily_cost": 265,
        "average_daily_cost_usd": 302,
        "places": (
            {
                "name": "Eiffel Tower",
                "category": "landmark",
                "description": "The iron tower offers panoramic views across Paris.",
                "image": "https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?auto=format&fit=crop&w=1200&q=80",
                "address": "Champ de Mars, 5 Avenue Anatole France, Paris",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "rating": 4.7,
                "best_time_to_visit": "Sunset",
                "estimated_cost": 36.10,
                "admission_fee_usd": 40.45,
                "estimated_visit_cost_usd": 56.03,
                "website": "https://www.toureiffel.paris/en/rates-opening-times",
            },
            {
                "name": "Louvre Museum",
                "category": "museum",
                "description": "A major art museum in a former royal palace, home to works from across history.",
                "image": "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?auto=format&fit=crop&w=1200&q=80",
                "address": "Rue de Rivoli, Paris",
                "latitude": 48.8606,
                "longitude": 2.3376,
                "rating": 4.8,
                "best_time_to_visit": "Weekday morning",
                "estimated_cost": 32,
                "admission_fee_usd": 35.86,
                "estimated_visit_cost_usd": 54.91,
                "website": "https://www.louvre.fr/en/visit/hours-admission",
            },
        ),
    },
    {
        "name": "Bali",
        "country": "Indonesia",
        "country_code": "ID",
        "description": "Tropical beaches, emerald rice terraces, and welcoming island culture.",
        "image": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=1200&q=80",
        "currency": "IDR",
        "language": "Indonesian",
        "timezone": "Asia/Makassar",
        "best_time": "April to October",
        "average_daily_cost": 1416950,
        "average_daily_cost_usd": 80,
        "places": (
            {
                "name": "Tegallalang Rice Terraces",
                "category": "nature",
                "description": "Stepped rice fields set among the green hills north of Ubud.",
                "image": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=1200&q=80",
                "address": "Tegallalang, Gianyar Regency, Bali",
                "latitude": -8.4319,
                "longitude": 115.2792,
                "rating": 4.6,
                "best_time_to_visit": "Early morning",
                "estimated_cost": 25000,
                "admission_fee_usd": 1.40,
                "estimated_visit_cost_usd": 6.99,
                "website": "https://www.indonesia.travel/gb/en/destinations/bali-nusa-tenggara/bali/tegallalang-rice-terraces",
            },
            {
                "name": "Uluwatu Temple",
                "category": "temple",
                "description": "A clifftop sea temple with wide ocean views and evening cultural performances.",
                "image": "https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?auto=format&fit=crop&w=1200&q=80",
                "address": "Pecatu, South Kuta, Badung Regency, Bali",
                "latitude": -8.8291,
                "longitude": 115.0849,
                "rating": 4.6,
                "best_time_to_visit": "Late afternoon",
                "estimated_cost": 50000,
                "admission_fee_usd": 2.79,
                "estimated_visit_cost_usd": 7.27,
                "website": "https://uluwatutemple.id/",
            },
        ),
    },
    {
        "name": "Singapore",
        "country": "Singapore",
        "country_code": "SG",
        "description": "Discover futuristic gardens, lively waterfronts, and renowned hawker food.",
        "image": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=1200&q=80",
        "currency": "SGD",
        "language": "English",
        "timezone": "Asia/Singapore",
        "best_time": "February to April",
        "average_daily_cost": 231,
        "average_daily_cost_usd": 181,
        "places": (
            {
                "name": "Gardens by the Bay",
                "category": "garden",
                "description": "A waterfront nature park featuring conservatories and the Supertree Grove.",
                "image": "https://images.unsplash.com/photo-1508964942454-1a56651d54ac?auto=format&fit=crop&w=1200&q=80",
                "address": "18 Marina Gardens Drive, Singapore",
                "latitude": 1.2816,
                "longitude": 103.8636,
                "rating": 4.7,
                "best_time_to_visit": "Late afternoon",
                "estimated_cost": 46,
                "admission_fee_usd": 35.92,
                "estimated_visit_cost_usd": 46.07,
                "website": "https://www.gardensbythebay.com.sg/en/things-to-do/attractions.html",
            },
            {
                "name": "Maxwell Food Centre",
                "category": "food",
                "description": "A popular hawker centre serving a wide range of local dishes.",
                "image": "https://images.unsplash.com/photo-1504215680853-026ed2a45def?auto=format&fit=crop&w=1200&q=80",
                "address": "1 Kadayanallur Street, Singapore",
                "latitude": 1.2806,
                "longitude": 103.8448,
                "rating": 4.4,
                "best_time_to_visit": "Lunch",
                "estimated_cost": 12,
                "admission_fee_usd": 0,
                "estimated_visit_cost_usd": 10.15,
                "website": "https://www.nea.gov.sg/our-services/hawker-management/overview",
            },
        ),
    },
    {
        "name": "Da Nang",
        "country": "Vietnam",
        "country_code": "VN",
        "description": "Golden bridges, nearby ancient streets, and a long stretch of sandy coastline.",
        "image": "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?auto=format&fit=crop&w=1200&q=80",
        "currency": "VND",
        "language": "Vietnamese",
        "timezone": "Asia/Ho_Chi_Minh",
        "best_time": "February to May",
        "average_daily_cost": 1450476,
        "average_daily_cost_usd": 56,
        "places": (
            {
                "name": "Marble Mountains",
                "category": "nature",
                "description": "A cluster of limestone hills with caves, pagodas, and city views.",
                "image": "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80",
                "address": "81 Huyen Tran Cong Chua, Ngu Hanh Son, Da Nang",
                "latitude": 16.0039,
                "longitude": 108.2632,
                "rating": 4.5,
                "best_time_to_visit": "Morning",
                "estimated_cost": 40000,
                "admission_fee_usd": 1.55,
                "estimated_visit_cost_usd": 6.96,
                "website": "https://danangfantasticity.com/en/marble-mountains",
            },
            {
                "name": "My Khe Beach",
                "category": "beach",
                "description": "A broad sandy beach along the coast of Da Nang.",
                "image": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
                "address": "Vo Nguyen Giap, Da Nang",
                "latitude": 16.0544,
                "longitude": 108.2476,
                "rating": 4.5,
                "best_time_to_visit": "Sunrise",
                "estimated_cost": 0,
                "admission_fee_usd": 0,
                "estimated_visit_cost_usd": 4.25,
                "website": "https://danangfantasticity.com/",
            },
        ),
    },
    {
        "name": "Reykjavik",
        "country": "Iceland",
        "country_code": "IS",
        "description": "Use the lively capital as a base for waterfalls, hot springs, and northern lights.",
        "image": "https://images.unsplash.com/photo-1504829857797-ddff29c27927?auto=format&fit=crop&w=1200&q=80",
        "currency": "ISK",
        "language": "Icelandic",
        "timezone": "Atlantic/Reykjavik",
        "best_time": "June to August for long days; September to March for auroras",
        "average_daily_cost": 37426,
        "average_daily_cost_usd": 307,
        "places": (
            {
                "name": "Hallgrimskirkja",
                "category": "landmark",
                "description": "A landmark church with a tower offering views over the capital.",
                "image": "https://images.unsplash.com/photo-1476610182048-b716b8518aae?auto=format&fit=crop&w=1200&q=80",
                "address": "Hallgrimstorg 1, Reykjavik",
                "latitude": 64.1417,
                "longitude": -21.9266,
                "rating": 4.6,
                "best_time_to_visit": "Clear day",
                "estimated_cost": 1500,
                "admission_fee_usd": 12.29,
                "estimated_visit_cost_usd": 40.14,
                "website": "https://www.hallgrimskirkja.is/en/visit",
            },
            {
                "name": "Harpa Concert Hall",
                "category": "culture",
                "description": "A glass-fronted concert hall and conference centre by the old harbour.",
                "image": "https://images.unsplash.com/photo-1473116763249-2faaef81ccda?auto=format&fit=crop&w=1200&q=80",
                "address": "Austurbakki 2, Reykjavik",
                "latitude": 64.1502,
                "longitude": -21.9324,
                "rating": 4.6,
                "best_time_to_visit": "Evening",
                "estimated_cost": 0,
                "admission_fee_usd": 0,
                "estimated_visit_cost_usd": 27.85,
                "website": "https://www.harpa.is/en/",
            },
        ),
    },
)


def get_catalog_user(db: Session) -> User:
    user = db.query(User).filter(User.email == CATALOG_EMAIL).first()
    if user is None:
        user = User(
            email=CATALOG_EMAIL,
            name="Public destination catalog",
            profile="System account that owns the public sample catalog.",
            hashed_password=hash_password(secrets.token_urlsafe(48)),
        )
        db.add(user)
        db.flush()
    return user


def seed_catalog(db: Session) -> tuple[int, int]:
    owner = get_catalog_user(db)
    destinations_created = 0
    places_created = 0

    for destination_data in DESTINATIONS:
        values = dict(destination_data)
        place_data = values.pop("places")
        destination = (
            db.query(Destination)
            .filter(
                Destination.name == values["name"],
                Destination.country_code == values["country_code"],
            )
            .first()
        )
        if destination is None:
            destination = Destination(**values, user_id=owner.id)
            db.add(destination)
            db.flush()
            destinations_created += 1
        else:
            destination.average_daily_cost = values["average_daily_cost"]
            destination.average_daily_cost_usd = values["average_daily_cost_usd"]

        for place_values in place_data:
            place = (
                db.query(Place)
                .filter(
                    Place.destination_id == destination.id,
                    Place.name == place_values["name"],
                )
                .first()
            )
            if place is None:
                db.add(Place(destination_id=destination.id, **place_values))
                places_created += 1
            else:
                place.estimated_cost = place_values["estimated_cost"]
                place.admission_fee_usd = place_values["admission_fee_usd"]
                place.estimated_visit_cost_usd = place_values[
                    "estimated_visit_cost_usd"
                ]
                place.website = place_values["website"]
                if place.image is None:
                    place.image = place_values["image"]

    db.commit()
    return destinations_created, places_created


def main() -> None:
    with SessionLocal() as db:
        destinations_created, places_created = seed_catalog(db)
    print(
        f"Catalog ready: added {destinations_created} destinations "
        f"and {places_created} places."
    )


if __name__ == "__main__":
    main()
