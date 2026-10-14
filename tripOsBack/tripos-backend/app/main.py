from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.accommodation import accommodations
from app.routes.admin import admin
from app.routes.ai import ai, ai_chat
from app.routes.ai import ai_conversations, ai_extractions, ai_messages
from app.routes.ai import document_parser
from app.routes.auth import auth
from app.routes.budget import budgets
from app.routes.budget import budget_categories
from app.routes.checklist import checklists
from app.routes.checklist import checklist_items
from app.routes.destination import destinations
from app.routes.document import documents
from app.routes.expense import expenses
from app.routes.expense import expense_splits
from app.routes.itinerary import itinerary
from app.routes.itinerary import itinerary_days, itinerary_items
from app.routes.memory import memories
from app.routes.memory import memory_photos
from app.routes.notification import notifications
from app.routes.packing import packing
from app.routes.packing import packing_lists
from app.routes.place import places
from app.routes.place import place_photos, place_tips
from app.routes.reminder import reminders
from app.routes.saved_place import saved_places
from app.routes.saved_place import saved_items
from app.routes.screenshot import screenshots
from app.routes.transport import transports
from app.routes.trip import trips
from app.routes.trip import trip_members, trip_wallets
from app.routes.user import users
from app.routes.wallet import wallet
from app.routes.wallet import wallet_transactions
from app.core.config import settings


app = FastAPI(title=settings.APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

for route_module in (
    auth,
    users,
    destinations,
    places,
    saved_places,
    saved_items,
    trips,
    itinerary,
    budgets,
    wallet,
    expenses,
    packing,
    checklists,
    accommodations,
    transports,
    documents,
    screenshots,
    reminders,
    notifications,
    memories,
    ai,
    ai_conversations,
    ai_chat,
    document_parser,
    ai_extractions,
    ai_messages,
    budget_categories,
    checklist_items,
    expense_splits,
    itinerary_days,
    itinerary_items,
    memory_photos,
    packing_lists,
    place_photos,
    place_tips,
    trip_members,
    trip_wallets,
    wallet_transactions,
    admin,
):
    app.include_router(route_module.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}