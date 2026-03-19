# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-04

## OVERVIEW

S&P 500 historical constituents data service (Python FastAPI + TypeScript/Next.js). Provides API/MCP access to real historical S&P 500 component lists sourced from Wikipedia.

## STRUCTURE

```
SP500/
├── app/                    # FastAPI backend
│   ├── main.py            # App factory + router registration
│   ├── models.py          # SQLAlchemy ORM models
│   ├── config/db.py       # Database configuration
│   ├── routers/          # API route handlers
│   │   ├── auth.py       # Login with email code
│   │   ├── billing.py    # Stripe subscription
│   │   ├── tokens.py     # API token CRUD
│   │   └── api.py        # S&P 500 data endpoint
│   └── utils/db.py       # DB session management
├── scripts/               # CLI tools
│   ├── sync_sp500.py     # Wikipedia data sync
│   └── mcp_server.py     # MCP server
├── templates/             # Jinja2 HTML templates
└── package.json          # Next.js frontend (NOT YET INTEGRATED)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| API endpoint | `app/routers/api.py` | Returns S&P 500 constituents by date |
| Auth flow | `app/routers/auth.py` | Email verification code login |
| Models | `app/models.py` | User, APIToken, SP500Constituent |
| Stripe billing | `app/routers/billing.py` | Subscription management |
| Data sync | `scripts/sync_sp500.py` | Wikipedia scraper |
| MCP server | `scripts/mcp_server.py` | Model Context Protocol |

## CODE MAP

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `create_app` | function | `app/main.py` | - | FastAPI app factory |
| `User` | model | `app/models.py` | 2 | Main user entity |
| `APIToken` | model | `app/models.py` | 1 | API token entity |
| `SP500Constituent` | model | `app/models.py` | 1 | Historical stock data |
| `get_sp500_constituents` | endpoint | `app/routers/api.py` | - | Main API route |

## CONVENTIONS

- **Python**: SQLAlchemy 2.0 style (Mapped, mapped_column)
- **Routing**: Router prefix pattern (`/auth`, `/billing`, `/tokens`, `/api`)
- **DB**: MySQL 8.4 + SQLAlchemy + Alembic migrations
- **Auth**: Email verification code (not password-based)

## ANTI-PATTERNS (THIS PROJECT)

- **Token validation incomplete**: `app/routers/api.py` line 21 - token validation logic is TODO
- **No .gitignore**: Project root missing standard Python ignores
- **No Alembic configs**: Migrations not set up despite Alembic in requirements.txt

## UNIQUE STYLES

- Hybrid stack: FastAPI backend + Next.js frontend (frontend not yet integrated)
- Data source: Wikipedia scraping for historical S&P 500 data
- MCP integration: Model Context Protocol server included

## COMMANDS

```bash
# Backend
uvicorn app.main:app --reload

# Sync data
python scripts/sync_sp500.py

# MCP server
python scripts/mcp_server.py

# Install deps
pip install -r requirements.txt
```

## NOTES

- Project has package.json with Next.js - frontend integration INCOMPLETE
- API token validation is a stub (security issue - needs implementation)
- Data sourced from Wikipedia, NOT S&P Dow Jones Indices (see license.html)