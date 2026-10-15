# TripOS Backend

TripOS Backend is a FastAPI service for travel planning. It uses SQLAlchemy for persistence, PostgreSQL for normal development/deployment, JWT bearer tokens for authentication, and Alembic for database schema migrations.

## Requirements

- Python 3.10 or newer
- PostgreSQL 14 or newer
- PowerShell on Windows, or a shell with the equivalent Python commands

## Project layout

```text
app/
	main.py                 FastAPI application and router registration
	core/
		config.py             Environment-backed application settings
		database.py           SQLAlchemy engine, base class, and DB session dependency
		security.py           Password hashing and JWT creation/validation
	models/                 SQLAlchemy database tables
	schemas/                Pydantic request and response validation
	controllers/            Auth, user, admin, and domain CRUD logic
	routes/                 HTTP endpoints; delegates work to controllers
	services/               Reusable service helpers for trips, budgets, uploads, AI, etc.
	utils/                  Small shared utility functions
tests/                    Pytest API tests; use an isolated in-memory SQLite database
migrations/
	env.py                  Alembic metadata and database configuration
	versions/               Generated, reviewed migration revisions
uploads/
	documents/              Document upload storage location
	screenshots/            Screenshot upload storage location
	memories/               Memory upload storage location
.env                      Local environment configuration
alembic.ini               Alembic migration configuration
requirements.txt          Python dependencies
```

### Request flow

An HTTP request enters through a module in `app/routes/`. Protected endpoints use `app/api/deps.py` to resolve the current user from a bearer token. The route calls a controller in `app/controllers/`; controllers own the database operations and authorization scope. SQLAlchemy models define persisted fields, while Pydantic schemas validate incoming and outgoing API data. `app/services/` contains helpers that can be shared across controllers.

The resource controllers share `ResourceController` for list, create, get, and delete behavior. These endpoints are user-scoped. Most resource types currently accept `name`, `description`, and a JSON `data` object, plus selected common fields such as dates, amount, currency, and category. Add fields to the relevant SQLAlchemy model and Pydantic schema when a domain requires stricter structure.

## Install and configure

From the project directory, create and activate a virtual environment:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create a PostgreSQL role and database. For example, from `psql` as a database administrator:

```sql
CREATE USER tripos_user WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE tripos_db OWNER tripos_user;
```

Copy `.env.example` to `.env` if `.env` is missing, then set values appropriate for your machine:

```dotenv
APP_NAME=TripOS API
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://tripos_user:choose-a-local-password@localhost:5432/tripos_db
JWT_SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

The repository ignores `.env` so local credentials are not committed. Set `OPENAI_API_KEY` on the API server to enable AI assistant replies; the key is never sent to the frontend. For OpenRouter, set `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, use your OpenRouter API key for `OPENAI_API_KEY`, and set `OPENAI_MODEL` to a model slug supported by OpenRouter. Restart the API server after changing its environment. If you want to create the database user with the sample credentials, run the SQL below in `psql`; otherwise use the username and password already configured in PostgreSQL:

```sql
CREATE USER tripos_user WITH PASSWORD 'change-me';
CREATE DATABASE tripos_db OWNER tripos_user;
```

If a password contains reserved URL characters, percent-encode them in `DATABASE_URL`. Replace the example JWT secret before deployment. Do not commit real credentials or production secrets.

## Database migrations

The application does not create or alter tables when it starts. Use Alembic to apply versioned schema changes. Make sure PostgreSQL is running and `DATABASE_URL` points to an existing database before running these commands from the project root.

The initial schema migration is checked in under `migrations/versions/`. For a new, empty database, apply it with:

```powershell
python -m alembic upgrade head
```

If you already have a database created by an earlier version of this app, do not run the initial migration against its existing tables. Back up the database first. If its schema exactly matches the checked-in baseline, mark that revision as applied without changing tables:

```powershell
python -m alembic stamp head
```

`stamp` only updates Alembic's version tracking; it does not create, alter, or verify tables. If the existing schema differs, compare it with the baseline and write an appropriate migration, or use a fresh development database and apply `upgrade head`.

For future model changes:

1. Update the SQLAlchemy model and its Pydantic schema.
2. Generate a revision: `python -m alembic revision --autogenerate -m "describe the change"`.
3. Review and, if necessary, edit the generated upgrade and downgrade operations.
4. Apply it locally with `python -m alembic upgrade head`.
5. Commit the migration file with the model and schema changes.

Useful commands:

```powershell
python -m alembic current
python -m alembic history
python -m alembic upgrade head
python -m alembic downgrade -1
```

Autogeneration is a starting point, not a substitute for reviewing the migration. Back up important databases before upgrades or downgrades. Test migrations against a disposable database before production.

## Populate the public catalog

The frontend loads destinations and recommended places from `GET /api/v1/destinations`
and `GET /api/v1/places`; these lists are not generated by the frontend. To add an
idempotent starter catalog to the configured database, run this after applying
migrations:

```powershell
python -m scripts.seed_catalog
```

The script adds sample destinations and places only when matching records are not
already present. It refreshes the curated catalog's cost estimates and official
venue links, fills missing place image URLs without replacing existing images,
and does not delete catalog data. Place image URLs are stored in the
`places.image` column and returned by the public places API.

Catalog place records keep `estimated_cost` and `admission_fee_usd` as the
admission charge in local currency and USD, respectively. A genuinely free
admission is recorded as zero. `estimated_visit_cost_usd` is a separate,
positive per-person estimate for one attraction visit; it is not a daily budget
or venue quote. Destination `average_daily_cost` and `average_daily_cost_usd`
are researched typical travel spending per person per day in local currency and
USD. The starter catalog uses Budget Your Trip's typical-traveler daily
benchmarks, based on aggregated traveler-reported costs for lodging, meals,
local transportation, and sightseeing (international travel to the destination
is excluded). Values are snapshots accessed October 11, 2026, not guaranteed
prices:

| Destination | Local amount/day | USD/person/day |
| --- | ---: | ---: |
| Kyoto | JPY 17,406 | $110 |
| Paris | EUR 265 | $302 |
| Bali | IDR 1,416,950 | $80 |
| Singapore | SGD 231 | $181 |
| Da Nang | VND 1,450,476 | $56 |
| Reykjavik | ISK 37,426 | $307 |

Sources: [Budget Your Trip methodology](https://www.budgetyourtrip.com/howitworks.php),
[Kyoto](https://www.budgetyourtrip.com/japan/kyoto),
[Paris](https://www.budgetyourtrip.com/france/paris),
[Bali](https://www.budgetyourtrip.com/indonesia/bali),
[Singapore](https://www.budgetyourtrip.com/singapore),
[Da Nang](https://www.budgetyourtrip.com/vietnam/da-nang), and
[Reykjavik](https://www.budgetyourtrip.com/iceland/reykjavik). These are
traveler-spending averages; actual costs vary by season, lodging, and itinerary.
Recheck current rates before travel.

Venue references used for the starter catalog:

- Kyoto: [Fushimi Inari Taisha](https://inari.jp/en/), [Kiyomizu-dera](https://www.kiyomizudera.or.jp/en/visit/)
- Paris: [Eiffel Tower](https://www.toureiffel.paris/en/rates-opening-times), [Louvre Museum](https://www.louvre.fr/en/visit/hours-admission)
- Bali: [Tegallalang Rice Terraces](https://www.indonesia.travel/gb/en/destinations/bali-nusa-tenggara/bali/tegallalang-rice-terraces), [Uluwatu Temple](https://uluwatutemple.id/)
- Singapore: [Gardens by the Bay](https://www.gardensbythebay.com.sg/en/things-to-do/attractions.html), [Maxwell Food Centre](https://www.nea.gov.sg/our-services/hawker-management/overview)
- Da Nang: [Marble Mountains](https://danangfantasticity.com/en/marble-mountains), [My Khe Beach](https://danangfantasticity.com/)
- Reykjavik: [Hallgrimskirkja](https://www.hallgrimskirkja.is/en/visit), [Harpa Concert Hall](https://www.harpa.is/en/)

The per-visit estimates use a modest local transport and meal allowance in
addition to admission: Fushimi Inari $10.74; Kiyomizu-dera $13.90; Eiffel Tower
(summit lift) $56.03; Louvre (non-EEA standard ticket) $54.91; Tegallalang
$6.99; Uluwatu Temple $7.27; Gardens by the Bay conservatories $46.07; Maxwell
Food Centre $10.15; Marble Mountains $6.96 (optional elevator included);
My Khe Beach $4.25; Hallgrimskirkja $40.14 (tower included); Harpa $27.85.
Tegallalang and Uluwatu admission amounts are provisional local reports rather
than official published tariffs. The Eiffel Tower, Louvre, Gardens by the Bay,
and Hallgrimskirkja ticket types/rates should be reconfirmed before visiting.

Saved backend places continue to use `POST /api/v1/saved-places`. Destination
and Wikipedia cards use the authenticated `POST /api/v1/saved-items` endpoint;
apply migrations with `python -m alembic upgrade head` before using it. Saved
items are private to the signed-in user and retain a snapshot of the item's
title, description, image, location, and source URL.

## Run the API

After dependencies are installed and migrations are applied:

```powershell
python -m uvicorn app.main:app --reload
```

By default, the service listens on `http://127.0.0.1:8000`.

- Interactive API docs: `http://127.0.0.1:8000/docs`
- Alternative docs: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/health`

To use another port: `python -m uvicorn app.main:app --reload --port 8001`.

## Run with Docker

Docker Compose runs the API and PostgreSQL with pinned image versions. The API installs the exact package versions in `requirements.lock`, waits for PostgreSQL, and applies Alembic migrations before starting. PostgreSQL data persists in the `postgres_data` volume.

Start the stack from the project directory:

```powershell
docker compose up --build
```

Open `http://localhost:8000/docs` for the API. To stop the containers while keeping the database, press `Ctrl+C` and run `docker compose down`. To also delete the stored database, run `docker compose down --volumes`.

Both developers should use the same committed `Dockerfile`, `compose.yaml`, and `requirements.lock`. To change the dependency set, update the lock file and commit it along with the code changes. The Compose defaults are for local development only; set `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` through a local `.env` file or environment variables before exposing the service beyond your machine.

## Authentication and API use

Register an account using `POST /api/v1/auth/register` with `email`, `password` (at least 8 characters), and optional `full_name`. Then log in using `POST /api/v1/auth/login` with the email and password. The response contains an `access_token`.

Destination and place catalogs can be browsed without an account using
`GET /api/v1/destinations`, `GET /api/v1/destinations/{id}`,
`GET /api/v1/places`, and `GET /api/v1/places/{id}`. All destinations and places
are shared in this public catalog. Creating or deleting catalog entries, and
using trip planning, saved places, or finance endpoints, still requires a token.

Send the token on protected requests using this header:

```text
Authorization: Bearer <access_token>
```

For example, after starting the server, use the Swagger UI at `/docs` to register, authorize, then try the protected endpoints. `GET /api/v1/users/me` returns the current account. Resource endpoints generally provide `GET` (list), `POST` (create), `GET /{id}` (fetch one), and `DELETE /{id}` operations. Users can only read or delete their own resources.

The authenticated `POST /api/v1/ai/parse-document` endpoint accepts multipart
form fields `file` and `trip_id`. It accepts JPEG, PNG, WebP, and PDF files up
to 10 MB; PDFs are limited to five pages. The API verifies that the signed-in
user owns the trip, then returns parsed `booking`, `expense`, and `reminder`
objects under a `parsed` key. Configure `OPENAI_API_KEY` and a vision-capable
`OPENAI_MODEL` on the backend. The endpoint extracts data only; the frontend
creates the returned trip records through their normal APIs.

### Route groups

- Authentication and account: `/api/v1/auth`, `/api/v1/users`
- Destinations and places: `/api/v1/destinations`, `/api/v1/places`, `/api/v1/saved-places`
- Trip planning: `/api/v1/trips`, `/api/v1/itineraries`
- Money: `/api/v1/budgets`, `/api/v1/wallets`, `/api/v1/expenses`
- Preparation and bookings: `/api/v1/packing`, `/api/v1/checklists`, `/api/v1/accommodations`, `/api/v1/transports`
- Travel records: `/api/v1/documents`, `/api/v1/screenshots`, `/api/v1/reminders`, `/api/v1/notifications`, `/api/v1/memories`
- AI request records: `/api/v1/ai/requests`
- Admin dashboard: `/api/v1/admin/dashboard`, `/api/v1/admin/users`,
  `/api/v1/admin/users/count`, `/api/v1/admin/destinations`,
  `/api/v1/admin/places`, `/api/v1/admin/reports`
- User-submitted reports: `/api/v1/reports`

Admin dashboard routes require an authenticated account whose email is listed in
`ADMIN_EMAILS` as a comma-separated allowlist. Set this variable in `.env` before
starting the API (or in the environment used by Docker Compose); for example,
`ADMIN_EMAILS=admin@example.com`. There is no public endpoint for granting admin
access. The dashboard supports paginated user, destination, place, and submitted
report lists. Authenticated users can submit reports with `POST /api/v1/reports`;
admins can review them with `PATCH /api/v1/admin/reports/{report_id}`.

The AI endpoint stores request records; it is not yet connected to an AI
provider. Document and screenshot resource endpoints currently store metadata;
production file upload/download endpoints and storage policies still need to be
implemented.

## Tests

Run the suite from the project root:

```powershell
python -m pytest
```

Tests override the configured database with in-memory SQLite and reset the tables per test. They do not require a running PostgreSQL server and do not test PostgreSQL-specific behavior or migrations.

## Before deployment

- Set a unique, strong `JWT_SECRET_KEY` and keep it secret.
- Configure PostgreSQL credentials through deployment environment variables or a secrets manager.
- Apply and verify Alembic migrations before starting application workers.
- Use private, durable file storage instead of relying on the local `uploads/` directories.
- Add role checks before treating admin routes as privileged.
- Configure HTTPS, CORS policy, logging, backups, and database connection/pool limits for the hosting environment.