# Accounts, authentication, and API keys

PK-DB owns its accounts, study permissions, and API keys. Browsers use server-side sessions; scripts use personal API keys. GitHub and ORCID are optional sign-in methods attached to a PK-DB account. Neither an external username nor a public profile reference grants a role.

This guide describes the implementation for issue #775. The [design specification](superpowers/specs/2026-09-22-authentication-user-management-design.md) also contains requirements beyond this implementation; consult the [implementation plan](superpowers/plans/2026-09-22-authentication-user-management.md) for remaining work.

## Roles and study access

| Role | Study permissions | Account and vocabulary administration |
| --- | --- | --- |
| `user` | Read public studies and explicitly granted private studies | None |
| `curator` | Upload new studies; edit only assigned studies | None |
| `reviewer` | Read and edit every study | None |
| `admin` | Read and edit every study; delete and manage study access | Designated `mkoenig` account only |

New registrations receive `user`. Users can request curator access through account settings; the administrator reviews pending requests. Reviewer promotion is an explicit administrator change. Creation assigns the uploader; subsequent scientific uploads cannot silently change assignments or visibility. Effective grants are separate from scientific contributor attribution.

The administrator account is bound to an internal ID in `security_configuration`. A partial unique index permits at most one `admin`. Existing installations with multiple administrators must reconcile those identities before applying the migration. Ordinary management endpoints cannot create a second administrator, demote the designated administrator, or suspend it.

## Deployment configuration

Serve the frontend and backend behind one HTTPS origin. Forward `/api/` and `/accounts/` to FastAPI, together with any enabled MCP route. Keep the frontend API base relative (`VUE_APP_API_BASE=""`). A browser origin includes the scheme, hostname and optional port, with no path.

| Environment variable | Production setting or behavior |
| --- | --- |
| `PKDB_DATABASE_URL` | PostgreSQL connection URL |
| `PKDB_FILE_ROOT` | Persistent managed file directory; includes avatars |
| `PKDB_BROWSER_ORIGIN` | Exact public origin, such as `https://pk-db.example.org` |
| `PKDB_SECURE_COOKIES` | `true` for HTTPS production |
| `PKDB_MFA_ENCRYPTION_KEY` | Persisted Fernet encryption key for administrator TOTP seeds |
| `PKDB_GITHUB_CLIENT_ID`, `PKDB_GITHUB_CLIENT_SECRET` | Enable GitHub sign-in when both are supplied |
| `PKDB_ORCID_CLIENT_ID`, `PKDB_ORCID_CLIENT_SECRET` | Enable ORCID sign-in when both are supplied |
| `PKDB_SMTP_HOST`, `PKDB_SMTP_SENDER` | Required to send verification, recovery and invitation mail |
| `PKDB_SMTP_PORT` | Defaults to `587` |
| `PKDB_SMTP_USERNAME`, `PKDB_SMTP_PASSWORD` | Optional SMTP authentication; provide both when required |
| `PKDB_SMTP_STARTTLS` | Defaults to `true`; SMTP transport uses STARTTLS, not implicit TLS |
| `PKDB_CORS_ORIGINS` | Explicit JSON array when needed; same-origin deployment normally needs none |

Production cookies are Secure, HttpOnly and SameSite=Lax, with `__Host-` names. Insecure cookies are restricted to local development hosts. Browser mutations require the expected Origin and a CSRF token obtained from `GET /api/v1/auth/csrf`; the frontend handles this automatically. An invalid explicit Authorization header does not fall back to a browser cookie.

The application needs outbound HTTPS to configured providers and outbound SMTP to its mail server. Missing SMTP settings leave mail-dependent actions unavailable; they must not be worked around by activating accounts manually. The current mail templates deliver one-use tokens. Invitation recipients can enter theirs at `/invitation`; verification and reset screens use the existing frontend routes.

Back up PostgreSQL, managed file storage, and the MFA encryption key together. Preserve provider credentials separately in deployment secret storage. Do not log Authorization headers, one-use tokens, OAuth callback queries, or request bodies from authentication routes.

## Administrator bootstrap and MFA

Apply migrations before provisioning accounts. From the repository root, with deployment environment variables set:

```bash
uv run --project backend pkdb create-admin mkoenig --email ADMIN_EMAIL
```

The command prompts for a password. For a reviewed existing active account, use its exact internal ID instead; adoption preserves its password:

```bash
uv run --project backend pkdb create-admin mkoenig --email ADMIN_EMAIL --adopt-user-id EXISTING_ID
```

Adoption requires matching ID, username and primary email. It does not reactivate a disabled or suspended account. `--password-stdin` is available for creating a new administrator, but must not be supplied when adopting one.

Generate a Fernet key once and save it in deployment secret storage:

```bash
uv run --project backend python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Set the result as `PKDB_MFA_ENCRYPTION_KEY` on every application instance. Do not generate a new value on each startup. Replacing it does not re-encrypt existing seeds; losing it makes those seeds unreadable.

After password or provider sign-in, `mkoenig` must enroll or verify an authenticator before administrator access. Enrollment displays a setup secret, requires a valid time-based code, and shows recovery codes once. Keep those codes securely; each is single-use. Administrator actions require recent account authentication and recent MFA. The account page provides **Confirm administrator identity** when assurance has expired.

For a lost authenticator and no usable recovery code, an operator with trusted database access can perform audited offline recovery:

```bash
uv run --project backend pkdb recover-admin-mfa mkoenig --user-id DESIGNATED_ID --confirm-recovery
```

This removes MFA enrollment and revokes sessions, API keys and account-action tokens. It preserves identity, password, role and account status. The administrator must sign in and enroll again. It does not bypass suspension or reset a password. Restore the original encryption key from backup where appropriate; do not silently replace the designated account.

## Existing curators and avatars

The reviewed public manifest is `backend/bootstrap/curator-roster.json`. Its source is `backend/pkdb_data/management/users.py` at revision `632a8bb21a894e97e2a4f6df7173f0956ded09f5`, containing 69 historical accounts. Reviewer identities are:

- Mariia Myshkina: `MariiaMysh`.
- Michelle Elias: `mii-halina`.
- Shubhankar Palwankar: `shubhankarpalwankar`.

`mkoenig` is provisioned through administrator bootstrap. Other historical curators remain curators, including former administrator `janekg`. The historical `reviewer` test account is excluded. Review the separately preserved `deepa`/`DeepaMahm` and `long231a`/`lucialink30` accounts before assigning contacts; the import does not merge them.

All roster members were checked against `livermetabolism-site`. There are 46 account-to-site-image mappings using 45 distinct images, plus existing PK-DB photos for `kgreen` and `xresearch`. The remaining 21 manifest entries have a local generic fallback, including the excluded test account. Site provenance is revision `6e13b9dff910434b9851296a073ff1642b277343`; the manifest records exact person mappings, source paths and checksums. Production uses copied assets and does not need the sibling checkout.

Validate the manifest, then preview the import:

```bash
python3 scripts/check_curator_roster.py
uv run --project backend pkdb import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --dry-run
```

The private contact overlay is a JSON list or CSV with `username`, optional `email`, optional exact `user_id`, and optional `assigned_study_ids`. CSV study IDs use semicolons. Keep contacts out of the public repository. Supply only reviewed addresses and explicit account/study mappings. For example:

```json
[
  {"username": "MariiaMysh", "email": "reviewed-contact@example.org", "user_id": 42, "assigned_study_ids": ["STUDY_ID"]}
]
```

Apply only after resolving dry-run conflicts:

```bash
uv run --project backend pkdb import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --apply
```

Changes to existing roles or explicit grants require `--update-existing`; add it to both preview and apply after reviewing the proposed differences. A conflicting primary address requires separate resolution. `--avatar-root` defaults to `frontend/public` and must contain the manifest's `assets/images/avatars/` paths. In a backend-only container, mount those assets and pass the corresponding root explicitly.

Dry runs create no accounts or asset files. Applying preserves existing IDs, credentials, suspension and user edits. New imported identities remain disabled. Matching import digests become no-ops, so rerunning the same manifest does not undo a later demotion or cleared photo. Invitations are a separate authenticated administrator action in **User administration → Invite**, or through `POST /api/v1/admin/users/{id}/invitations` with a reviewed `email_id`. The dialog shows the reviewed primary contact and requires an explicit send; failures allow a retry. Unclaimed accounts cannot be activated instead of completing verification. Acceptance claims that identity without changing its assigned role. Imported GitHub/ORCID references are public metadata, not sign-in credentials.

## GitHub and ORCID setup

Register these exact callback URLs with the respective provider, replacing the origin with `PKDB_BROWSER_ORIGIN`:

```text
https://pk-db.example.org/api/v1/auth/github/callback
https://pk-db.example.org/api/v1/auth/orcid/callback
```

The implementation uses Authlib's synchronous `requests_client.OAuth2Session` adapter and the declared `requests` dependency. GitHub requests `read:user`; ORCID requests `/authenticate`. The current ORCID endpoints are the production `orcid.org` service, not its sandbox. Provider buttons appear only when both client ID and secret are configured. Credentials must match the registered callback and provider environment.

New provider identities complete username/contact-email onboarding and PK-DB verification before activation. Existing accounts link providers explicitly in account settings after recent authentication; email matches never merge accounts. GitHub is identified by its stable numeric ID and ORCID by the returned authenticated iD. A self-entered or imported handle remains distinct from an authenticated connection. Unlinking must leave a usable sign-in method.

Invited users may choose a password at `/invitation`, or use GitHub/ORCID and select **I have an invitation for an existing account** after returning from the provider. Submitting the invitation token links that proved identity to the existing imported account, verifies the invited primary contact, and preserves its role and study assignments. No new username is required. The invitation and browser-bound provider proof are consumed together; expired, already used, suspended-account, or conflicting-identity claims are rejected.

Validate real provider registration, consent, callback routing and mail delivery in a staging deployment before enabling public sign-in. Automated provider tests use controlled responses; they do not prove that live provider credentials or console settings are correct.

## Sessions, keys and compatibility

Browser login no longer returns an API key. The frontend clears old local-storage credentials and keeps profile state only in memory. Sessions have a seven-day absolute lifetime and a 24-hour idle limit. Profile and credential management require a browser session; keys cannot issue other keys or manage accounts.

Create a named personal key in **Account settings → API keys**. The secret is displayed once. Keys default to `read` and 90 days, with a maximum of 365 days and ten live keys per account. Curators, reviewers and the administrator can request `studies:write` in addition to `read`. These scopes never bypass current role, account state or study assignments.

Send keys using `Authorization: Bearer KEY` over HTTPS. The CLI continues to accept `PKDB_API_TOKEN`. REST and MCP use the same credential restrictions. Rotation creates a replacement and allows at most 24 hours of overlap, bounded by the old key's expiry. Revocation is immediate for subsequent authorization checks. Password recovery and account suspension revoke sessions and API keys.

`POST /api-token-auth/` is retired and returns `410`. Existing legacy API tokens have a fixed transition window: migration `p775import01` stores its application time plus 30 days in `security_configuration.legacy_token_cutoff`. This deadline is persisted once, not renewed at process startup or by rerunning imports. Missing or expired configuration denies legacy credentials. Replace scripts' tokens with personal keys before the stored cutoff. Do not treat legacy tokens as browser sessions.

## Profiles and operations

Account settings includes **Assigned studies** with study links and **Security history** with recent account events. Both lists are paginated and use the current account’s permissions; changing accounts clears previously loaded activity.

Profiles support display name, affiliation, title, GitHub reference and ORCID reference. Primary and secondary email addresses are private. Users can independently hide their GitHub and ORCID references from public profiles while retaining connected sign-in methods; hidden references and their provenance remain visible to the account owner. Usernames are immutable through profile editing. Uploaded photos are validated JPEG, PNG or WebP, bounded to 5 MiB and 16 megapixels, and re-encoded into managed thumbnails. Animated content and arbitrary remote image URLs are rejected. Users can remove their photo; a later import preserves that choice. Imported small WebP thumbnails retain their original bytes; other supported images are normalized.

Rate counters are shared in PostgreSQL across keys for an account. Initial ordinary-request limits are 30/minute for anonymous IPs, 120/minute per account and 60/minute per key, with an additional authenticated IP ceiling of 600/minute. Dedicated login, registration, upload and export budgets also apply. `429` responses include `Retry-After`. HTTP requests also hold shared PostgreSQL concurrency leases through response streaming, with expiry and renewal to recover capacity after worker failure. Defaults are six concurrent requests per account and two per anonymous IP; uploads and exports additionally have one-per-account and shared global limits. The existing process-local upload guard still bounds request bodies.

The ordinary budgets can be configured with `PKDB_QUOTA_ANONYMOUS_PER_MINUTE`, `PKDB_QUOTA_ACCOUNT_PER_MINUTE`, `PKDB_QUOTA_KEY_PER_MINUTE`, `PKDB_QUOTA_IP_PER_MINUTE`, `PKDB_QUOTA_UPLOADS_PER_HOUR`, and `PKDB_QUOTA_EXPORTS_PER_MINUTE`. Concurrent-request settings are `PKDB_QUOTA_ACCOUNT_CONCURRENCY` and `PKDB_QUOTA_ANONYMOUS_CONCURRENCY`; global upload/export settings are `PKDB_UPLOAD_CONCURRENCY` and `PKDB_EXPORT_CONCURRENCY`. Inject overrides into the backend environment. `PKDB_RATE_LIMITS_ENABLED=false` disables admission limits and is intended for controlled testing. The administrator account page includes read-only selected-user usage counters and a paginated security audit table. Per-account quota overrides remain implementation-plan work.

Avatar replacement removes superseded files. A rolled-back import can leave an unreferenced file; `pkdb cleanup` removes these after a one-day grace period. It also removes expired OAuth transactions, concurrency leases, throttle counters, credentials expired more than 30 days ago, and audit events older than 365 days. Schedule this maintenance regularly.

## Frontend development and validation

The development frontend proxies `/api` and `/accounts` to `http://127.0.0.1:8000`, with an empty API base. Match `PKDB_BROWSER_ORIGIN` to the frontend's actual local origin, normally `http://localhost:8080`. The Compose backend host port defaults to `18083`; when using it directly, adjust the development proxy target or expose the backend on `8000`.

The frontend uses Node 22 and Dart Sass. Its existing Vue CLI/Webpack version requires the OpenSSL compatibility flag; frontend Dockerfiles set it:

```bash
cd frontend
npm install
NODE_OPTIONS=--openssl-legacy-provider npm run build
NODE_OPTIONS=--openssl-legacy-provider npm run test:unit -- --exit
```

The production build and authentication component tests passed during implementation. The build retains existing bundle-size warnings. A connected browser was unavailable, so interactive visual QA was not completed. Before deployment, check desktop/mobile account layout, password and provider onboarding, administrator MFA/recovery, photo upload/removal, email verification, key creation/revocation, and reviewer/curator access using a staging database and mail service.
