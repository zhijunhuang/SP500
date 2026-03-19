# app/routers

## OVERVIEW

FastAPI route handlers for SP500 data service.

## ROUTERS

| File | Prefix | Purpose |
|------|--------|---------|
| `auth.py` | `/auth` | Email verification code login |
| `billing.py` | `/billing` | Stripe subscription management |
| `tokens.py` | `/tokens` | API token CRUD operations |
| `api.py` | `/api` | S&P 500 data endpoints |

## ENDPOINTS

- `GET /auth/login` - Login page
- `POST /auth/send-code` - Send 6-digit verification code
- `POST /auth/verify-code` - Verify code, auto-register user
- `GET /billing/subscribe` - Subscription page
- `POST /billing/create-checkout-session` - Create Stripe checkout
- `GET /tokens` - Token management page
- `POST /tokens/create` - Create new API token
- `POST /tokens/delete` - Revoke token
- `POST /tokens/copy` - Duplicate existing token
- `GET /api/sp500/{date}` - Get S&P 500 constituents by date

## ANTI-PATTERNS

- **Hardcoded user_id**: All token endpoints use `user_id = 1` (line 22, 46, 70, 95 in tokens.py)
- **No email sending**: Verification codes printed to console only (auth.py line 46)
- **Token validation stub**: api.py line 21 - authorization header accepted but never validated
- **Webhook stub**: billing.py line 75 - webhook handler returns success without processing
- **Auto-registration**: Users auto-created on first login (no approval flow)

## NOTES

- Session management NOT implemented - all routes use hardcoded user_id=1
- Data source: Wikipedia, NOT S&P Dow Jones Indices