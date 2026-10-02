# Authentication

> **Status:** Implemented — Phase 3. Reflects `backend/app/api/v1/auth.py` and `backend/app/core/security.py`.

The API uses **bearer tokens (JWT)**. A client exchanges credentials for a token
once, then sends that token on every subsequent request.

## Flow

```
POST /api/v1/auth/register   →  201 Created (user, no credentials echoed back)
POST /api/v1/auth/login      →  200 OK      { access_token, token_type, expires_in }
GET  /api/v1/users/me        →  200 OK      Authorization: Bearer <access_token>
```

## Endpoints

| Method | Path | Auth | Success | Purpose |
|---|---|---|---|---|
| POST | `/api/v1/auth/register` | none | 201 | Create an account |
| POST | `/api/v1/auth/login` | none | 200 | Exchange credentials for a token |
| GET | `/api/v1/users/me` | bearer | 200 | Read the caller's profile |
| PATCH | `/api/v1/users/me` | bearer | 200 | Partially update the caller's profile |

### `POST /api/v1/auth/register`

```json
{ "email": "candidate@example.com", "password": "supersecret123", "full_name": "Ada Lovelace" }
```

- `email` must be a valid address; it is lower-cased and trimmed before storage.
- `password` must be 8–128 characters and must not start or end with whitespace.
- `full_name` is optional.

Responses: `201` with the created user, `409` if the email is taken,
`422` if validation fails.

### `POST /api/v1/auth/login`

```json
{ "email": "candidate@example.com", "password": "supersecret123" }
```

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer", "expires_in": 3600 }
```

Responses: `200`, `401` for bad credentials, `403` if the account is disabled.

## Token format

Signed with `HS256` using `JWT_SECRET`. Claims:

| Claim | Meaning |
|---|---|
| `sub` | User id (string) |
| `iat` | Issued-at (UTC) |
| `exp` | Expiry (UTC), `iat` + `JWT_EXPIRE_MINUTES` |
| `typ` | Always `access` — tokens of any other type are rejected |

Decoding is strict: signature, expiry, algorithm, type and subject are all
validated, and any failure returns `401` with a `WWW-Authenticate: Bearer`
challenge.

## Security properties

- **Passwords are hashed with bcrypt** and never stored, logged, or returned.
  No response schema includes a password field.
- **No account enumeration.** An unknown email and a wrong password produce the
  *identical* `401` body, so the endpoint cannot be used to test whether an
  address is registered.
- **Fails closed.** Malformed hashes, empty tokens and tampered signatures all
  deny access rather than erroring open.
- **Revocation is by lookup.** The user is re-read from the database on every
  authenticated request, so deleting or disabling an account invalidates its
  outstanding tokens immediately.

> Tokens are stateless and there is no refresh-token flow yet. Short expiry
> plus server-side user lookup is the current revocation strategy; refresh
> tokens and a token denylist are tracked for Phase 8 (Production Hardening).

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `JWT_SECRET` | `change-me` | **Must be overridden in every deployed environment.** |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_EXPIRE_MINUTES` | `60` | Token lifetime in minutes |
| `CORS_ORIGINS` | `*` | Comma-separated allow-list; never `*` in production |
