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
FIREBASE_PROJECT_ID=your-firebase-project-id
```

The repository ignores `.env` so local credentials are not committed. Set `OPENAI_API_KEY` on the API server to enable AI assistant replies; the key is never sent to the frontend. For OpenRouter, set `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, use your OpenRouter API key for `OPENAI_API_KEY`, and set `OPENAI_MODEL` to a model slug supported by OpenRouter. Restart the API server after changing its environment. If you want to create the database user with the sample credentials, run the SQL below in `psql`; otherwise use the username and password already configured in PostgreSQL:

Set `FIREBASE_PROJECT_ID` to enable Google sign-in. The frontend sends Firebase ID
tokens to `/api/v1/auth/google`; the API verifies their signature, issuer,
audience, expiry, and verified-email claim against Firebase's public signing
keys before creating or signing in a Komsan account. Firebase service-account
credentials are not needed by this flow. Send the Firebase ID token (for example,
`await user.getIdToken()`) as `id_token` or `idToken`, not a Google OAuth access
token. The API allows up to 60 seconds of clock skew when checking token
timestamps; keep the API host clock synchronized.

Set `GOOGLE_VISION_API_KEY` on the backend to enable OCR for booking screenshots
and PDFs. The key is used only by the API server and must not be added to a
frontend `VITE_` variable, which would expose it in the browser bundle.

To send a welcome email at account creation and a welcome-back email on every
successful password or Google sign-in, configure `GMAIL_CLIENT_ID`,
`GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, and `GMAIL_USER` (or
`GMAIL_FROM_EMAIL`) for a Google OAuth client authorized to send mail with the
Gmail API. `GMAIL_FROM_NAME` is optional.
Both welcome and reminder emails include a clickable `Komsan | Travel planner`
link. Set `WEBSITE_URL` to the frontend URL; it defaults to
`http://localhost:5173` for local development. Set it to the publicly accessible
HTTPS website URL before sending emails to users, since `localhost` links only
work on the device running the frontend. On Render, set
`WEBSITE_URL=https://deoloy-front-end-python.vercel.app`.
The API reports whether the email was accepted, failed, or is not configured in
registration, password-login, and Google sign-in responses. Password login
accepts `send_welcome_email: false` to suppress the email when an account
creation flow has already sent one. Gmail accepting a message does not guarantee
Inbox placement; recipients may need to check Spam or configure their own Gmail
filters. Email delivery problems do not prevent account creation or sign-in.
Keep Gmail OAuth credentials only in the backend environment, never in the
frontend.

Pending reminders are emailed once to the saved email address on the owning
account when they become due. A reminder completed after its due time is still
emailed; reminders completed before their due time and cancelled reminders are
not. For Google sign-in, this is the verified email address on the account. The
email is a brief notification with the reminder title and due time; the
configured Gmail mailbox is the sender. The API checks every 60 seconds, so
delivery can be up to about one minute after the due time. Reminder and
notification email due times are displayed in Cambodia time
(`Asia/Phnom_Penh`, UTC+07:00); stored timestamps remain UTC.
Reminder email uses Gmail API OAuth, independently of Firebase sign-in.
Enable the Gmail API in Google Cloud,
create an OAuth client, authorize the sending mailbox with the
`https://www.googleapis.com/auth/gmail.send` scope, and configure the resulting
client ID, client secret, refresh token, and mailbox address in the backend:

```dotenv
GMAIL_CLIENT_ID=your-oauth-client-id
GMAIL_CLIENT_SECRET=your-oauth-client-secret
GMAIL_REFRESH_TOKEN=your-oauth-refresh-token
GMAIL_USER=authorized-sender@gmail.com
GMAIL_FROM_NAME=Komsan
```

The API uses the refresh token to obtain short-lived access tokens and sends
from that authorized mailbox. This OAuth mailbox is the sender; reminder
notifications are addressed to each owning user's saved account email.
`GMAIL_FROM_EMAIL` is also accepted as an alias
for `GMAIL_USER`. The refresh token must be the actual token returned after
granting the `gmail.send` scope; a placeholder value does not enable sending.
A Google API key or Firebase sign-in token cannot
replace these OAuth credentials. Keep all OAuth credentials on the backend and
never put them in frontend `VITE_` variables. The worker remains disabled until
all four required credentials are present and the API is restarted. Reminder
delivery failures are retried on a later worker pass. If OAuth consent is in
Testing mode, Google may expire refresh tokens after seven days. When using
Docker Compose, put the settings in the Compose `.env` file as well.
To verify a reminder in the sender's Gmail Sent folder, reauthorize the same
OAuth client with both `https://www.googleapis.com/auth/gmail.send` and
`https://www.googleapis.com/auth/gmail.readonly`, then replace
`GMAIL_REFRESH_TOKEN` and restart the backend. From the backend project folder,
run:

```powershell
python -m scripts.verify_gmail_sent --to you@example.com --subject "Reminder due: your reminder title"
```

Use the intended recipient and exact subject for the reminder being checked.
This confirms whether the configured sending mailbox has the message in Sent;
it cannot confirm delivery to the recipient's inbox.
For Gmail HTTP 403 failures, check the logged Google `reason` and `message`:
`insufficientPermissions` or `ACCESS_TOKEN_SCOPE_INSUFFICIENT` means the
refresh token was not authorized with `gmail.send`; authorize the mailbox with
that scope, replace the refresh token, and restart the API. `accessNotConfigured`
means Gmail API must be enabled in the Google Cloud project used by the OAuth
client. Workspace policy errors may require the administrator to allow the app.

Every Komsan account uses its own saved email as the recipient, regardless of
whether it signed in with a password or Google. Gmail is only the sender; the
recipient is looked up from the reminder owner's account when delivery occurs.
This supports different valid recipient addresses, subject to Gmail API quotas
and the recipient provider's spam/delivery rules. Each account receives email
for the reminders it creates; logging into a second Komsan account does not
change or copy reminders created by the first account.

For hosting, configure the Gmail OAuth values above as backend environment
secrets and use a persistent PostgreSQL database. The reminder processor runs
inside the API by default when `EMAIL_WORKER_ENABLED=true`, checking every
`EMAIL_WORKER_INTERVAL_SECONDS` (default 60). If the hosting provider sleeps
or scales API processes to zero, deploy a separate always-on worker from the
same backend image with the command `python -m app.workers.email_worker` and
set `EMAIL_WORKER_ENABLED=false` on the API service to avoid relying on API
lifespan for scheduled delivery. The worker must use the same database and
Gmail settings as the API; apply `python -m alembic upgrade head` as a deploy
step before starting it. Set `WEBSITE_URL` to the public HTTPS frontend URL and
configure `CORS_ORIGINS` for the frontend origin when the frontend and API use
different origins.

Notifications created through `/api/v1/notifications` can also be emailed at a
scheduled `due_date`. Include `due_date` as an ISO 8601 timestamp when creating
or updating a notification; leave it unset for notifications that should only
appear in the app. Due notification emails go to the owning account's saved
email address, are retried after delivery failures, and are sent once after
success. Notification due times use the same Gmail OAuth settings and
60-second worker as reminders.

Alternatively, install [Ollama](https://ollama.com/download), download a model such as `llama3.2:3b` with `ollama pull llama3.2:3b`, and set these backend `.env` values to run chat locally without a provider key:

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_MODEL=llama3.2:3b
```

Start Ollama and restart the API server after changing the configuration.

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
- Admin dashboard: `/api/v1/admin/dashboard`,
  `/api/v1/admin/dashboard/analytics`, `/api/v1/admin/users`,
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
Dashboard analytics aggregate trip creations and itinerary items over the
latest seven calendar months and group them by destination region. OCR category
and human-review rates are calculated from persisted AI extraction records.
Successful `/api/v1/ai/parse-document` requests create a completed extraction;
documents with no recognized booking, expense, or reminder are marked as
requiring human review. The `requires_human_review` field can also be updated
through the AI extraction resource API.
Admins can permanently delete another user with
`DELETE /api/v1/admin/users/{user_id}`; associated account data is removed,
creator ownership of destination catalog entries is cleared, and an admin
cannot delete their own account.

The AI request endpoint stores request records; it is not yet connected to an
AI provider. Document and screenshot resource endpoints currently store
metadata; production file upload/download endpoints and storage policies still
need to be implemented.

## Tests

Run the suite from the project root:

```powershell
python -m pytest
```

Tests override the configured database with in-memory SQLite and reset the tables per test. They do not require a running PostgreSQL server and do not test PostgreSQL-specific behavior or migrations.

## Deploy to Render

The repository-root `render.yaml` defines the Docker web service. In Render, choose **New +** > **Blueprint**, connect this repository, and deploy the Blueprint. It builds from `tripOsBack/tripos-backend/Dockerfile`, applies Alembic migrations at startup, and serves the health check at `/health`.

Before deploying, create a Render PostgreSQL database in the same region as the web service. Set `DATABASE_URL` on the web service to the database's **Internal Database URL**. Set `CORS_ORIGINS` to a JSON array containing your frontend's origin, for example:

```text
["https://your-frontend.example.com"]
```

Render generates `JWT_SECRET_KEY` for the service. Set `OPENAI_API_KEY` only if you use the AI features. After deployment, verify the service at `https://<your-service>.onrender.com/health`.

### Copy local SQLite data to Render

Alembic creates or updates the schema; it does not copy records from a local
SQLite database. To migrate existing local records, use Render's **External
Database URL** from your local machine. Run these commands from the backend
project directory in PowerShell:

```powershell
$env:TARGET_DATABASE_URL = Read-Host "Paste Render's External Database URL"
python -m scripts.migrate_sqlite_to_render --source .\tripos_dev.db
```

Review the dry-run output, then copy records with:

```powershell
python -m scripts.migrate_sqlite_to_render --source .\tripos_dev.db --apply
Remove-Item Env:TARGET_DATABASE_URL
```

The command preserves primary keys and copies all non-empty tables in
foreign-key order. It never deletes data and stops if a destination table
already contains records, so do not clear production tables to make it run.
The external database URL is read from the process environment and is not
written to the repository.

The free web service has an ephemeral filesystem. Uploaded trip covers and memory photos stored under `uploads/` can disappear when the service restarts or redeploys. Use persistent file storage for production uploads; a Render persistent disk requires a paid service plan.

## Before deployment

- Set a unique, strong `JWT_SECRET_KEY` and keep it secret.
- Configure PostgreSQL credentials through deployment environment variables or a secrets manager.
- Apply and verify Alembic migrations before starting application workers.
- Use private, durable file storage instead of relying on the local `uploads/` directories.
- Add role checks before treating admin routes as privileged.
- Configure HTTPS, CORS policy, logging, backups, and database connection/pool limits for the hosting environment.