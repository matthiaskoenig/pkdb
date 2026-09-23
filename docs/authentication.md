# Accounts, authentication, and API keys

PK-DB owns its accounts, study permissions, and API keys. Browsers use server-side sessions; scripts use personal API keys. Users sign in with a username and password. GitHub and ORCID are optional, editable profile references only; they do not authenticate users or grant roles. MFA is not used.

This guide describes the current password-based account flows. Earlier authentication design documents are historical and include provider and MFA requirements that have been removed.

Public study browsing and filter overviews are available without signing in. Data downloads through `/api/v1/filter/?download=true` and study attachments under `/media/` require an authenticated, active account, including for public studies. Scripts should authenticate with a personal API key. Downloads include only studies and attachments the account can access.

## Roles and study access

| Role | Study permissions | Account and vocabulary administration |
| --- | --- | --- |
| `user` | Read public studies and explicitly granted private studies | None |
| `curator` | Upload new studies; edit only assigned studies | None |
| `reviewer` | Read and edit every study | None |
| `admin` | Read and edit every study; delete and manage study access | Designated administrator account only |

New registrations receive `user`. Users can request curator access through account settings; the administrator reviews pending requests. Reviewer promotion is an explicit administrator change. Creation assigns the uploader; subsequent scientific uploads cannot silently change assignments or visibility. Effective grants are separate from scientific contributor attribution.

The administrator account is bound to an internal ID in `security_configuration`. A partial unique index permits at most one `admin`. Existing installations with multiple administrators must reconcile those identities before applying the migration. Ordinary management endpoints cannot create a second administrator, demote the designated administrator, or suspend it.

## Deployment configuration

Serve the frontend and backend behind one HTTPS origin. Forward `/api/` and `/accounts/` to FastAPI, together with any enabled MCP route. Keep the frontend API base relative (`VITE_API_BASE=""`). A browser origin includes the scheme, hostname and optional port, with no path.

| Environment variable | Production setting or behavior |
| --- | --- |
| `PKDB_DATABASE_URL` | PostgreSQL connection URL |
| `PKDB_FILE_ROOT` | Persistent managed file directory; includes avatars |
| `PKDB_BROWSER_ORIGIN` | Exact public origin, such as `https://pk-db.example.org` |
| `PKDB_SECURE_COOKIES` | `true` for HTTPS production |
| `PKDB_SMTP_HOST`, `PKDB_SMTP_SENDER` | Required to send verification, recovery and invitation mail |
| `PKDB_SMTP_PORT` | Defaults to `587` |
| `PKDB_SMTP_USERNAME`, `PKDB_SMTP_PASSWORD` | Optional SMTP authentication; provide both when required |
| `PKDB_SMTP_STARTTLS` | Defaults to `true`; SMTP transport uses STARTTLS, not implicit TLS |
| `PKDB_CORS_ORIGINS` | Explicit JSON array when needed; same-origin deployment normally needs none |

Production cookies are Secure, HttpOnly and SameSite=Lax, with `__Host-` names. Insecure cookies are restricted to local development hosts. Browser mutations require the expected Origin and a CSRF token obtained from `GET /api/v1/auth/csrf`; the frontend handles this automatically. An invalid explicit Authorization header does not fall back to a browser cookie.

SMTP is needed for public registration verification, password recovery, and invitations. Existing active accounts with a password can sign in without SMTP. Local development accounts can be provisioned directly with the operator command below. Invitation recipients enter their one-use token at `/invitation` and choose a password.

Back up PostgreSQL and managed file storage together. Do not log Authorization headers, one-use tokens, passwords, or request bodies from authentication routes.

## Local development accounts

After applying migrations, create an active account with a password:

```bash
uv run --project backend pkdb create-user developer
```

The command prompts for a password; it needs no email, mail server, external provider, or authenticator. Use `--role curator --email developer@example.org` for local API-key upload testing or `--role reviewer` to test reviewer access. API-key creation requires a verified primary contact; the operator-supplied `--email` creates that contact without mail delivery. For browser login, email is optional; `--password-stdin` supports scripted provisioning without placing the password in command arguments. Existing identities are not overwritten. Sign in using the new username and password.

## Administrator bootstrap

Replace `USERNAME` and `ADMIN_EMAIL` with your chosen username and email. Apply migrations before provisioning accounts. From the repository root, with deployment environment variables set:

```bash
uv run --project backend pkdb create-admin USERNAME --email ADMIN_EMAIL
```

The command prompts for a password. For a reviewed existing active account, use its exact internal ID instead; adoption preserves its password:

```bash
uv run --project backend pkdb create-admin USERNAME --email ADMIN_EMAIL --adopt-user-id EXISTING_ID
```

Adoption requires matching ID, username and primary email. It does not reactivate a disabled or suspended account. `--password-stdin` is available for creating a new administrator, but must not be supplied when adopting one.

The administrator signs in with the same username/password form. A valid administrator session is sufficient for administration. Sensitive personal account changes, including API-key creation, may ask for the password again after ten minutes. No authenticator enrollment, one-time code, provider credential, or encryption key is needed.

## Existing curators and avatars

The reviewed public manifest is `backend/bootstrap/curator-roster.json`. Its source is `backend/pkdb_data/management/users.py` at revision `632a8bb21a894e97e2a4f6df7173f0956ded09f5`, containing 69 historical accounts. Reviewer identities are:

- Mariia Myshkina: `MariiaMysh`.
- Michelle Elias: `mii-halina`.
- Shubhankar Palwankar: `shubhankarpalwankar`.

The administrator is provisioned through administrator bootstrap with a chosen username. The historical administrator roster entry is skipped unless it matches that designated account. Other historical curators remain curators, including former administrator `janekg`. The historical `reviewer` test account is excluded. Review the separately preserved `deepa`/`DeepaMahm` and `long231a`/`lucialink30` accounts before assigning contacts; the import does not merge them.

All roster members were checked against `livermetabolism-site`. There are 46 account-to-site-image mappings using 45 distinct images, plus existing PK-DB photos for `kgreen` and `xresearch`. The remaining 21 manifest entries have a local generic fallback, including the excluded test account. Site provenance is revision `6e13b9dff910434b9851296a073ff1642b277343`; the manifest records exact person mappings, source paths and checksums. Production uses copied assets and does not need the sibling checkout.

Validate the manifest, then preview the import:

```bash
python3 scripts/check_curator_roster.py
uv run --project backend pkdb import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --dry-run
```

The private contact overlay is a JSON list or CSV with `username`, optional `email`, optional exact `user_id`, and optional `assigned_study_ids`. Study IDs are internal positive integer IDs; CSV study IDs use semicolons. Keep contacts out of the public repository. Supply only reviewed addresses and explicit account/study mappings. For example:

```json
[
  {"username": "MariiaMysh", "email": "reviewed-contact@example.org", "user_id": 42, "assigned_study_ids": [123]}
]
```

Apply only after resolving dry-run conflicts:

```bash
uv run --project backend pkdb import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --apply
```

Changes to existing roles or explicit grants require `--update-existing`; add it to both preview and apply after reviewing the proposed differences. A conflicting primary address requires separate resolution. `--avatar-root` defaults to `frontend/public` and must contain the manifest's `assets/images/avatars/` paths. In a backend-only container, mount those assets and pass the corresponding root explicitly.

Dry runs create no accounts or asset files. Applying preserves existing IDs, credentials, suspension and user edits. New imported identities remain disabled. Matching import digests become no-ops, so rerunning the same manifest does not undo a later demotion or cleared photo. Invitations are a separate authenticated administrator action in **User administration → Invite**, or through `POST /api/v1/admin/users/{id}/invitations` with a reviewed `email_id`. The dialog shows the reviewed primary contact and requires an explicit send; failures allow a retry. Unclaimed accounts cannot be activated instead of completing verification. Acceptance claims that identity without changing its assigned role. Imported GitHub/ORCID references are public metadata, not sign-in credentials.

## Optional GitHub and ORCID references

Users can add, edit, clear, or hide their GitHub username and ORCID iD in their profile. These values are metadata only. There are no provider sign-in buttons, callbacks, linking flows, or provider account creation.

Migration `p788simpleauth01` preserves existing profile references and changes authenticated provenance to self-asserted. It signs out existing browser sessions once, requiring a fresh password login, while preserving API keys. It removes external identity records, OAuth transactions, MFA secrets, and session MFA timestamps. Existing active accounts that only used provider login must set a password using their verified-email password reset before their next login. The migration does not activate accounts or invent passwords. Downgrading restores empty authentication tables, not removed credentials or secrets.

## Sessions, keys and compatibility

Browser login no longer returns an API key. The frontend clears old local-storage credentials and keeps profile state only in memory. Sessions have a seven-day absolute lifetime and a 24-hour idle limit. Profile and credential management require a browser session; keys cannot issue other keys or manage accounts.

Create a named personal key in **Account settings → API keys**. The secret is displayed once. Keys default to `read` and 90 days, with a maximum of 365 days and ten live keys per account. Curators, reviewers and the administrator can request `studies:write` in addition to `read`. These scopes never bypass current role, account state or study assignments.

Send keys using `Authorization: Bearer KEY` over HTTPS. The CLI continues to accept `PKDB_API_TOKEN`. REST and MCP use the same credential restrictions. Rotation creates a replacement and allows at most 24 hours of overlap, bounded by the old key's expiry. Revocation is immediate for subsequent authorization checks. Password recovery and account suspension revoke sessions and API keys.

`POST /api-token-auth/` is retired and returns `410`. Existing legacy API tokens have a fixed transition window: migration `p775import01` stores its application time plus 30 days in `security_configuration.legacy_token_cutoff`. This deadline is persisted once, not renewed at process startup or by rerunning imports. Missing or expired configuration denies legacy credentials. Replace scripts' tokens with personal keys before the stored cutoff. Do not treat legacy tokens as browser sessions.

## Profiles and operations

Account settings includes **Assigned studies** with study links and **Security history** with recent account events. Both lists are paginated and use the current account’s permissions; changing accounts clears previously loaded activity.

Profiles support display name, affiliation, title, GitHub reference and ORCID reference. Primary and secondary email addresses are private. Users can independently hide their GitHub and ORCID references from public profiles; hidden references and their provenance remain visible to the account owner. Usernames are immutable through profile editing. Uploaded photos are validated JPEG, PNG or WebP, bounded to 5 MiB and 16 megapixels, and re-encoded into managed thumbnails. Animated content and arbitrary remote image URLs are rejected. Users can remove their photo; a later import preserves that choice. Imported small WebP thumbnails retain their original bytes; other supported images are normalized.

Rate counters are shared in PostgreSQL across keys for an account. Initial ordinary-request limits are 30/minute for anonymous IPs, 120/minute per account and 60/minute per key, with an additional authenticated IP ceiling of 600/minute. Dedicated login, registration, upload and export budgets also apply. `429` responses include `Retry-After`. HTTP requests also hold shared PostgreSQL concurrency leases through response streaming, with expiry and renewal to recover capacity after worker failure. Defaults are six concurrent requests per account and two per anonymous IP; uploads and exports additionally have one-per-account and shared global limits. The existing process-local upload guard still bounds request bodies.

The ordinary budgets can be configured with `PKDB_QUOTA_ANONYMOUS_PER_MINUTE`, `PKDB_QUOTA_ACCOUNT_PER_MINUTE`, `PKDB_QUOTA_KEY_PER_MINUTE`, `PKDB_QUOTA_IP_PER_MINUTE`, `PKDB_QUOTA_UPLOADS_PER_HOUR`, and `PKDB_QUOTA_EXPORTS_PER_MINUTE`. Concurrent-request settings are `PKDB_QUOTA_ACCOUNT_CONCURRENCY` and `PKDB_QUOTA_ANONYMOUS_CONCURRENCY`; global upload/export settings are `PKDB_UPLOAD_CONCURRENCY` and `PKDB_EXPORT_CONCURRENCY`. Inject overrides into the backend environment. `PKDB_RATE_LIMITS_ENABLED=false` disables admission limits and is intended for controlled testing. The administrator account page includes read-only selected-user usage counters and a paginated security audit table. Per-account quota overrides remain implementation-plan work.

Avatar replacement removes superseded files. A rolled-back import can leave an unreferenced file; `pkdb cleanup` removes these after a one-day grace period. It also removes expired concurrency leases, throttle counters, credentials expired more than 30 days ago, and audit events older than 365 days. Schedule this maintenance regularly.

## Frontend development and validation

Use [Local setup and development](installation.md) for the Docker frontend or native Vite workflow. The host Vite proxy defaults to `http://127.0.0.1:18083`; the Docker frontend uses `http://backend:8000`. The default browser origin is `http://localhost:8080`.

The frontend uses the pinned Node 24.21.x and npm 12.1.x versions with Vite:

```bash
cd frontend
npm ci
npm run dev
npm run typecheck
npm run test:unit
npm run build
```

The isolated browser acceptance harness is documented in [local upload testing](local-upload-testing.md#isolated-frontend-browser-checks). It exercises password login without provider credentials or MFA. Mail delivery and production proxy configuration still require validation in the target environment.
