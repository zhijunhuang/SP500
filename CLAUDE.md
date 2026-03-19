# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

S&P 500 historical constituents data service. Provides API and MCP access to real historical S&P 500 component lists sourced from Wikipedia. Based on concepts from "Stocks on the Move" by Andreas F. Clenow about the importance of historically accurate constituent data for backtesting.

**Stack**: Pure Python/FastAPI. The `package.json` with Next.js dependencies exists but is NOT used - all frontend is Jinja2 templates.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Sync S&P 500 data from Wikipedia
python scripts/sync_sp500.py

# Start MCP server
python scripts/mcp_server.py
```

## Architecture

### Backend Structure (`app/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app factory, router registration, startup events |
| `models.py` | SQLAlchemy 2.0 ORM models (User, APIToken, SP500Constituent, EmailLoginCode, SP500Meta) |
| `config/db.py` | **Hardcoded** MySQL connection parameters (host, port, user, password, dbname) |
| `utils/db.py` | Database engine creation, SessionLocal, init_db(), get_db() dependency |
| `routers/auth.py` | Email verification code login (passwordless), session management via itsdangerous |
| `routers/billing.py` | Stripe subscription handling ($10/year), checkout sessions, webhooks |
| `routers/tokens.py` | API token CRUD (create/copy/delete), SHA-256 hashed storage |
| `routers/api.py` | Main data endpoint `/api/sp500/{date}` - requires valid token + active subscription |

### Database

- **Engine**: MySQL 8.4 + SQLAlchemy 2.0 (DeclarativeBase, mapped_column, Mapped types)
- **Connection**: Built in `utils/db.py` using credentials from `config/db.py`
- **Initialization**: `init_db()` creates all tables on startup via `@app.on_event("startup")`
- **Models use**: SQLAlchemy 2.0 style with type hints (`Mapped[int] = mapped_column(...)`)

### Key Models

```python
User                    # email, stripe_customer_id, subscription_status
APIToken               # user_id, name, token_hash (SHA-256), revoked
SP500Constituent       # code, company_name, sector, industry, effective_from, effective_to
EmailLoginCode         # email, code, created_at, used (5-minute expiry)
SP500Meta              # key/value store for data_source, last_sync, etc.
```

### Authentication Flow

1. User requests login code at `/auth/login`
2. 6-digit code generated, stored in `EmailLoginCode` table (5-min expiry)
3. Code sent via SMTP (logs to console if SMTP not configured)
4. User submits code at `/auth/verify-code`
5. Session cookie set (itsdangerous signed, 24-hour expiry)
6. `require_current_user` dependency protects routes

### API Access Pattern

```bash
# 1. Login via web UI to create account
# 2. Subscribe via Stripe ($10/year)
# 3. Create API token at /tokens
# 4. Use token to access data:
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/sp500/2024-01-01
```

### Data Synchronization (`scripts/sync_sp500.py`)

- Scrapes Wikipedia "List of S&P 500 companies" page
- Compares against current database records (effective_to IS NULL)
- Marks removed constituents with effective_to date
- Adds new constituents with effective_from = today
- Updates SP500Meta with last_sync timestamp

### MCP Server (`scripts/mcp_server.py`)

- Exposes `get_constituents(date)` method via Model Context Protocol
- No authentication on MCP endpoint (different from HTTP API)

## Environment Variables

Create `.env` file (see `.env.example`):

```bash
SECRET_KEY=           # Required: Session/itsdangerous signing key
DATABASE_URL=         # Optional: overrides config/db.py hardcoded values
STRIPE_API_KEY=       # Stripe secret key (sk_test_... or sk_live_...)
STRIPE_PRICE_ID=      # Price ID for $10/year subscription
STRIPE_WEBHOOK_SECRET=# Webhook signing secret (optional for dev)
SMTP_HOST=            # Email server (optional, logs to console if not set)
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
FROM_EMAIL=
BASE_URL=http://localhost:8000  # Used for Stripe redirect URLs
```

## Router Prefixes

| Router | Prefix | Key Routes |
|--------|--------|------------|
| auth | `/auth` | /login, /send-code, /verify-code, /logout |
| billing | `/billing` | /subscribe, /create-checkout-session, /webhook |
| tokens | `/tokens` | / (list), /create, /delete, /copy |
| api | `/api` | /sp500/{date}, /meta |

## Important Implementation Notes

1. **Hardcoded DB credentials**: `app/config/db.py` contains plaintext credentials (admin/passw0rd). In production, migrate to environment variables.

2. **Token storage**: API tokens are SHA-256 hashed in DB; plain token shown only once at creation.

3. **Subscription checking**: API endpoint checks `user.subscription_status == "active"` - Stripe webhooks update this field.

4. **No Alembic**: Despite being in requirements.txt, migration setup is incomplete. Database tables created via `Base.metadata.create_all()`.

5. **Unused package.json**: Contains Next.js dependencies but frontend is pure Jinja2 templates in `templates/`. The TypeScript/Next.js setup is not being used.

6. **Data source**: Wikipedia scraping, NOT official S&P Dow Jones Indices data. See `license.html` for usage restrictions.

7. **Email in development**: If SMTP not configured, verification codes are printed to server console.

## Testing Authentication

```bash
# 1. Start server
uvicorn app.main:app --reload

# 2. Login via browser at http://localhost:8000/auth/login
#    (Check terminal for verification code if SMTP not configured)

# 3. Complete Stripe subscription (use test card 4242 4242 4242 4242)

# 4. Create API token at http://localhost:8000/tokens

# 5. Test API:
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/sp500/2024-01-15
```
