# Authentication, user management, and API keys

Date: 2026-09-22. Issue: [#775 - Improved user authentification and management, API keys](https://github.com/matthiaskoenig/pkdb/issues/775). Status: Implementation specification. This document specifies future behavior; it does not describe functionality already delivered.

## 1. Scope and decisions

Extend the existing FastAPI/PostgreSQL application with usable account registration, GitHub and ORCID sign-in, browser sessions, independently managed personal API keys, consistent permissions, and protection against excessive crawler and agent traffic. Retain PK-DB ownership of accounts, roles, study access, and API keys. Use Authlib for external login protocols rather than implementing OAuth/OIDC primitives. An external identity service such as Keycloak is outside this implementation.

The user explicitly requires four roles: users can read; curators can upload and change only assigned studies; reviewers can change all studies; administrators manage measurement types and other privileged operations. Existing curators must be populated without losing their study relationships. `USERNAME` is the only administrator. Registration must support email/password, GitHub, and ORCID.

The default role is `user`. For initial population, use the existing curator definitions in the user-specified `users.py`, with explicit reviewer overrides for Mariia Myshkina, Michelle Elias, and Shubhankar Palwankar. This existing-account roster is distinct from the default for newly registered accounts; its precise import mapping is specified in section 10.

The remaining choices in this document are implementation defaults from the design proposal: public anonymous browsing remains available, deletion and access-control changes are administrator-only, newly uploaded studies start private, API keys default to read-only, and administrator access requires MFA. These defaults are explicit so implementation does not silently invent policy. This specification supersedes conflicting authentication and authorization behavior in the backend replacement specification; unrelated scientific and ingestion contracts remain unchanged.

## 2. Existing foundation and gaps

| Location | Current behavior and required change |
| --- | --- |
| `backend/src/pkdb/db/models/users.py` | Users, email addresses, hashed purpose-specific tokens, and account throttles exist. Change the user role default from `curator` to `user`; add the credential and identity records below. |
| `backend/src/pkdb/services/accounts.py` | Registration explicitly creates ordinary users; verification, password reset, and throttling exist. Reuse these services and extend recovery/session behavior. |
| `backend/src/pkdb/services/authentication.py` | Opaque API tokens are hashed and expire after 30 days by default. Separate browser sessions from personal API keys. |
| `backend/src/pkdb/services/authorization.py` | Reviewers can read private studies but cannot write globally; membership can currently grant writes without a curator role. Replace with section 3. |
| `backend/src/pkdb/services/ingestion.py` | Permissions are rechecked during publication, but uploaded graphs can replace study metadata and relationships. Protect access-control fields and preserve credential scope during rechecks. |
| `backend/src/pkdb/services/admin_users.py` | Administrative creation issues an API token and accepts role changes. Replace automatic credential issuance with invitations and enforce the sole-administrator invariant. |
| `backend/src/pkdb/mcp/authentication.py` | Tokens are checked against the database, with a generic `pkdb` scope. Preserve immediate rechecks and enforce actual key scopes per tool. |
| `backend/src/pkdb/commands/admin.py` | Administrator creation rejects existing identities. Add explicit, verified adoption of the existing `USERNAME` account. |
| `backend/src/pkdb/db/bootstrap.py` and `backend/bootstrap/users.json` | Bootstrap role defaults need tightening; the roster is currently empty. Add a private, reviewed account import. |
| `frontend/src/store.js` and frontend API callers | Browser tokens are kept in local storage. Replace this with cookie sessions and centralized request handling. |

## 3. Authorization contract

### 3.1 Role matrix

Every authenticated operation requires an active account. New registrations receive `user`; no registration or provider callback can choose a privileged role.

| Operation | Anonymous | User | Curator | Reviewer | Administrator |
| --- | --- | --- | --- | --- | --- |
| Browse public study data | Yes, limited | Yes | Yes | Yes | Yes |
| Read private study data | No | Explicit read grant | Explicit read grant or curator assignment | All studies | All studies |
| Download public files with open licence | Yes, limited | Yes | Yes | Yes | Yes |
| Read private or closed-licence files | No | Explicit read grant | Explicit read grant or curator assignment | All studies | All studies |
| Create own API keys | No | Yes | Yes | Yes | Yes |
| Upload a new study | No | No | Yes | Yes | Yes |
| Validate or edit an existing study | No | No | Assigned studies | All studies | All studies |
| Delete a study | No | No | No | No | Yes |
| Change assignments, read grants, creator, visibility, or licence | No | No | No | No | Yes |
| Change measurement types or shared vocabulary | No | No | No | No | Yes |
| Manage users, roles, account suspension, and quotas | No | No | No | No | Yes |

Preserve existing explicit creator/collaborator read access when migrating. Creator attribution alone must not confer write access. A curator assignment confers read access but confers write access only while the account has the curator role. A reviewer has read/write access to every study, including private studies, without modifying its assignment list. Downgrading a reviewer removes this global access.

All users can read public content; registration does not make private studies or restricted files public. Search, counts, exports, file downloads, and MCP results must apply the same visibility rules and must not disclose inaccessible study metadata.

### 3.2 Content and access-control separation

Study edits include scientific data, study descriptions, and attachments. Access-control operations are distinct from content edits. Separate effective curator assignments and read grants from scientific contributor attribution, even if the source format uses the same usernames for both.

On creation, automatically assign the authenticated uploader as a curator and record the uploader as creator. Non-administrative creation starts private; it cannot add effective grants for other accounts. Require a licence value, and reserve subsequent licence changes for the administrator. Reject source requests that conflict with these rules with field-specific validation errors. Administrator corpus imports may explicitly preserve legacy creator, visibility, licence, and assignments.

On replacement, authorize against the existing published study before processing its proposed relationships. Reject unauthorized changes to protected fields atomically. Preserve effective assignments and grants independently of graph replacement; removing a contributor from an uploaded source must not implicitly revoke a grant, and adding one must not grant access. Where existing formats mix these concepts, the adapter must compare protected values and provide an actionable error rather than silently discarding them. An administrator changes effective grants through explicit management operations.

Apply identical checks to REST, MCP, CLI-backed API calls, validation, file staging/finalization, replacement, deletion, exports, and vocabulary operations. File staging must be bounded and require write capability; attaching files additionally requires permission on the target study. Local maintenance commands are trusted operator interfaces, must enforce account invariants, and must not be reachable as ordinary API endpoints.

### 3.3 Effective permission and concurrency

For API keys, effective access is the intersection of current account permissions, key scopes, and current study access. Browser sessions use current account permissions and study access. Unknown roles/actions/scopes deny access.

Extend `Principal` to carry credential kind, credential ID, and immutable granted scopes in addition to account identity. Reload account state without losing credential restrictions. Do not reconstruct a scope-free principal when entering ingestion or other services.

Recheck active state, credential revocation/expiry, role, assignment, and scopes inside the committing transaction for writes. Use a consistent locking/versioning strategy shared with role changes, suspension, key revocation, and assignment changes. A permission change committed before a write's final authorization check must prevent that write. Already completed operations or bytes already streamed cannot be recalled; document this boundary. MCP must reauthorize each tool invocation, not just session initialization.

### 3.4 Sole administrator

Persist the designated administrator's internal user ID in a singleton security configuration record. Bootstrap explicitly binds it to the reviewed existing `USERNAME` identity or creates that identity if absent. Reserve the `USERNAME` username before enabling public registration. Never derive privilege from an external username, email, request field, or provider claim.

Enforce at most one `admin` with a PostgreSQL partial unique index and enforce the designated ID in the role-management service. Ordinary role endpoints accept only `user`, `curator`, and `reviewer`. Prevent deletion, demotion, or suspension of the sole administrator through ordinary account management. Reject conflicting pre-existing administrators during migration and report them for explicit resolution; do not silently demote users. A controlled offline recovery command may restore access to the designated account and must audit its actions.

## 4. Account lifecycle and external identities

### 4.1 Registration and account settings

Keep email/password registration with verified email and Argon2 password hashing. Pending users cannot obtain a normal session, API key, or privileged action until activation. Keep account status separate from email verification: verifying an address must never reactivate a suspended account.

Account settings show profile, verified addresses, linked providers, role, assigned studies, active sessions, API keys, and recent security events. Users can request curator access with a short reason; the administrator can approve or reject it. Reviewer promotion is an explicit administrator action. Changes of role and account status are audited.

Use generic registration/recovery responses that do not reveal whether an email is registered. Rate-limit registration, login, email sending, recovery, and invitations by both account/address and source IP. Apply consistent canonicalization and uniqueness rules to email addresses; do not apply provider-specific transformations such as stripping dots or plus suffixes.

### 4.2 GitHub and ORCID

Support sign-in and registration through GitHub OAuth and ORCID OAuth/OIDC. Use authorization-code flows, exact registered callbacks, state validation, PKCE where supported, and OIDC issuer/audience/signature/nonce validation where applicable. Provider secrets and temporary tokens stay server-side. Provider enablement and callback URLs are explicit deployment configuration; unavailable providers show an understandable error without affecting password login.

Identify GitHub accounts by stable numeric ID and ORCID accounts by authenticated ORCID iD/issuer and subject. Do not identify accounts by mutable usernames. Request minimal sign-in/profile permissions and no repository access or ORCID record-writing permissions. Do not retain provider access/refresh tokens after sign-in unless a separately specified feature requires them.

A new external identity creates a pending ordinary account and completes contact-email verification. A verified email supplied by a provider may prefill the form, but PK-DB verifies contact ownership itself. ORCID email availability must not be assumed. A short-lived onboarding credential may complete registration only; it is not a normal API credential.

Linking a provider to an existing account requires a current session and recent reauthentication. Never automatically merge accounts by matching email, display name, username, or a public ORCID identifier. If an email belongs to another account, require sign-in/recovery for that account and then explicit linking. Enforce uniqueness of `(provider, issuer, subject)` transactionally; concurrent linking attempts must not attach an identity to two accounts.

Unlinking requires recent authentication and must leave at least one usable login method. Provider-only accounts may establish a password through verified recovery. External login never changes roles, assignments, or account suspension. Administrator login via any provider still requires PK-DB MFA.

### 4.3 Recovery, invitations, and administrator MFA

Verification, reset, invitation, onboarding, OAuth-state, and recovery credentials are purpose-bound, expire, and are single-use where applicable. Store digests of bearer secrets; redeem tokens atomically. Do not consume invitation/reset tokens on GET, since email link scanners may follow links. Complete consumption on an explicit POST.

Initial expiry defaults: email verification 24 hours, password reset 30 minutes, invitation 7 days, OAuth transaction/onboarding 10 minutes. Rate-limit retries and resends. Mail failure must leave a recoverable pending state, never an activated account without proof of ownership.

Require TOTP MFA for `USERNAME`, using a maintained library, encrypted TOTP seed storage with an operational secret, and hashed single-use recovery codes. Enrollment requires authenticated bootstrap or recent account authentication; prove a valid code before activation. Prevent replay within a TOTP time step and rate-limit failures. A partially authenticated session cannot perform administrative operations or issue keys. Administrator recovery must use recovery codes or the audited offline recovery command, not email reset alone.

Password reset revokes all browser sessions and personal API keys, with a clear notice that scripts need replacement keys. Suspension revokes all sessions and keys and blocks all login methods; reactivation does not revive revoked credentials. Users can revoke other sessions and all keys when reporting compromise.

### 4.4 Minimal user profile

Keep registration short: require a username and primary email, plus a password only for password registration. Provide an avatar for every account without requiring a photo upload. All other profile fields are optional. Separate profile information from credentials and server-managed authorization fields.

| Field | Requirement and representation | Visibility |
| --- | --- | --- |
| `username` | Required, unique PK-DB handle; maximum 150 characters; preserved for existing users | Public when the account is attributed on public content |
| `email` | Required primary contact address; verified before activation; backed by `EmailAddress`, not a second independent source of truth | Owner and administrator only |
| `avatar_url` | Read-only URL for a locally managed image, or a deterministic initials/generic fallback; photo upload is optional | Public when displayed with public attribution |
| `display_name` | Optional preferred/full name, maximum 200 characters; falls back to username; accept Unicode without requiring Western first/last-name structure | Public when displayed with public attribution |
| `affiliation` | Optional institution/group text, maximum 250 characters; one free-text field initially | Public profile field |
| `title` | Optional academic/professional title, e.g. `Dr.` or `Prof. Dr.`, maximum 100 characters; never an authorization role | Public profile field |
| `github` | Optional GitHub profile handle, rendered as a canonical profile link; display metadata is separate from the stable authenticated provider ID | Public profile field if supplied |
| `orcid` | Optional ORCID iD, normalized to the hyphenated identifier, including valid checksum; rendered as an HTTPS ORCID link | Public profile field if supplied |
| `second_email` | Optional distinct secondary contact/recovery address; independently verified and unique across accounts | Owner and administrator only |

The main addition to the requested fields is `display_name`: scientific attribution needs a readable name independently of the login handle. Preserve existing `first_name` and `last_name` for compatibility, backfill `display_name` where possible, and make `display_name` the canonical UI label rather than forcing new users to maintain all three. Keep title separate from the name; do not infer or strip titles from imported names without an explicit mapping.

Use stable internal user IDs for all relationships. Keep usernames immutable through self-service in this release because source studies refer to them; any later administrative rename requires alias/reference migration. Prevent case-insensitive username collisions for new accounts and report existing collisions before adding constraints. Display names, affiliation, title, and images never confer privileges. Render free-text fields as escaped plain text, not HTML.

Do not add phone number, postal address, date of birth, gender, biography, or a required homepage. Multiple affiliations, institutional identifiers, and expanded professional profiles are outside the initial scope. Internal account ID, role, status, verification state, timestamps, and provenance are necessary operational metadata, not registration fields.

### 4.5 Profile privacy, email, and provider ownership

Public responses contain only an explicit allowlist of profile fields; never serialize primary/secondary email, session/key metadata, last login, or account recovery information. Showing contributor profiles must not reveal private study memberships or expose a public directory of all registered accounts. Profile editors label which fields may be shown publicly. Users can remove optional fields and their photo; scientific attribution and security retention remain governed by their separate policies.

Use existing email-address records for primary and secondary email; profile responses derive those values rather than duplicating writable columns. Support one primary and one secondary address in the initial UI. Preserve any additional existing addresses during migration and report them rather than deleting them. Address replacement remains pending until verified and does not discard the previous working primary address. Switching primary requires recent authentication and verification of the new address; notify the old and new addresses. Reject removal of the primary address without a verified replacement. A secondary address becomes eligible for password recovery only after verification; both addresses use the same non-enumerating recovery flow. Email recovery does not bypass administrator MFA.

GitHub and ORCID may be supplied as optional profile references without enabling social login. Distinguish `self_asserted`/`imported` profile references from `authenticated` identities in storage and UI. Only a completed provider ownership flow can attach login credentials or mark the reference authenticated. Editing a public reference must never relink a credential. If a linked provider exists, display its authenticated identifier and require the explicit unlink/link flow to change it. Never infer ownership from an imported link or image. Keep provider identity records even if the owner opts not to display their public reference.

### 4.6 Avatars and initial profile population

Use images from `livermetabolism-site` wherever an explicit identity match is available. The inspected source repository is `/home/USERNAME/git/livermetabolism-site`; its people metadata is `data/people.yml`, and existing 128-pixel WebP thumbnails are in `public/assets/image/people/128/`. Use these thumbnails directly for initial avatars rather than fetching photos from external providers or generating replacements.

| PK-DB identity to resolve | Site person ID | Existing thumbnail relative to `public/assets/image/people/128/` |
| --- | --- | --- |
| `USERNAME` | `matthias_koenig` | `matthias_koenig.webp` |
| Mariia Myshkina | `mariia_myshkina` | `mariia_myshkina.webp` |
| Michelle Elias | `michelle_elias` | `michelle_elias.webp` |
| Shubhankar Palwankar | `shubhankar_palwankar` | `shubhankar_palwankar.webp` |

These assets exist in the inspected checkout. Extend the explicit mapping to other roster members with available images; site person IDs are not assumed to be PK-DB usernames. The import manifest records target user ID/username, source person ID, source revision, relative asset path, and image checksum. The site roster supplies profile/image metadata only, never PK-DB roles or proof of account ownership. GitHub/ORCID references in `people.yml` may populate imported profile references but cannot create login links. Do not infer affiliation/title from the site's employment role or assume missing contact details.

Copy mapped images into PK-DB-managed persistent asset storage during the explicit import step and serve stable local URLs. Production must not depend on the sibling checkout, external hotlinks, or live access to `livermetabolism-site`. Reuse the original source assets and record provenance. Import missing images as fallbacks with a report; never choose a different person's photo by approximate name matching. Routine imports fill missing profile fields only and must not overwrite user edits, replacement photos, or an explicit photo removal. Track initialized/removed state where needed to distinguish an empty field from a request to clear it.

Allow users to upload, replace, or remove their avatar through account settings. Accept JPEG, PNG, and WebP, at most 5 MiB and 16 megapixels decoded; validate actual image content, reject SVG/animation, strip metadata, and re-encode a bounded square thumbnail of up to 256 pixels using maintained image-processing tooling. Do not upscale imported 128-pixel thumbnails. Store generated filenames outside executable paths and apply upload quotas. Arbitrary remote image URLs are not accepted. After removal, show local initials from display name/username or a generic icon; do not call Gravatar or disclose email hashes to third parties. Delete superseded files once no references remain under the normal asset cleanup policy.

## 5. Browser sessions

Use a random opaque session secret with a digest in PostgreSQL. Send it in a Secure, HttpOnly, SameSite=Lax, host-only cookie in production, preferably with a `__Host-` name. Serve frontend and API through the same origin. Local HTTP development may use a separately named non-Secure cookie; production must not permit that setting.

Default idle timeout is 24 hours and absolute lifetime is 7 days. Rotate the session on login, privilege elevation, and MFA completion. Administrative actions, provider linking/unlinking, email/password changes, and key creation require authentication within the last 10 minutes; administrative actions also require recent MFA. Server-side logout revokes the current session and clears the cookie. Logout does not revoke separately issued API keys.

Protect every cookie-authenticated mutation, including login and logout, with CSRF tokens and Origin validation. Use explicit CORS origins; never wildcard credentialed CORS. Do not store session/API/provider secrets in local storage, JavaScript-readable persistent cookies, URLs, analytics, or logs. OAuth callback parameters must be redacted and immediately removed by redirect. Pages handling one-time secrets use `Cache-Control: no-store` and a restrictive referrer policy.

Centralize frontend HTTP authentication and error handling. A request with an explicit invalid Authorization header fails rather than falling back to a cookie. If a valid API key is supplied, its scopes remain effective even when a browser session is also present. API keys cannot call session-only account/administrator endpoints.

## 6. Personal API keys

Keys are independently created by an active, verified user in account settings. Use at least 256 bits of cryptographic randomness and a recognizable versioned prefix such as `pkdb_live_`. Persist only the digest and non-secret display prefix; show the complete key once in the creation response. Never provide a retrieve-secret endpoint. Redact Authorization headers across proxy, application, error, and MCP logging.

Each key has owner, name, prefix, digest, immutable scopes, creation time, expiry, last-used time, revocation time, and optional rotation lineage. Default expiry is 90 days; configurable maximum is 365 days, with no non-expiring keys. Default limit is 10 unrevoked, unexpired keys per user, enforced transactionally. Last-used updates may be coalesced to once per five minutes to avoid write amplification.

| Scope | Capability | Eligible roles |
| --- | --- | --- |
| `read` | Read authorized study data/files; ordinary query/export operations within quotas | User, curator, reviewer, administrator |
| `studies:write` | Create, validate, and replace studies and their attachments within current study permissions | Curator, reviewer, administrator |

Default to `read`; write keys request both scopes. Reject unknown or ineligible scopes. Keys cannot change vocabulary, delete studies, change access controls, manage accounts, or create more keys, including keys owned by the administrator. These operations require an interactive session. Automated administrator workflows would require a separate future design.

Accept keys as `Authorization: Bearer <key>` over HTTPS for REST and MCP. Never accept them in query parameters. CLI tooling continues using `PKDB_API_TOKEN` or an equivalent explicit secret input and never prints the value.

Demotion immediately reduces effective access; promotion does not expand the scopes of an existing key. Scope changes require issuing a replacement. Rotation creates a new key and leaves the old one valid for an explicit overlap interval, default 24 hours and bounded by its original expiry. Users can revoke the old key immediately. The interface clearly shows the overlap deadline. Revoke operations are idempotent.

## 7. Data model and migrations

Use Alembic migrations and database constraints. Keep existing user IDs, historical attribution, and valid password hashes. Do not rebuild the database.

| Record | Required fields and constraints |
| --- | --- |
| User | Existing identity/profile; role defaults to `user`; explicit pending/active/suspended state or equivalent constrained representation; no conflation of suspension and verification |
| User profile | Optional display name, affiliation, title, avatar asset reference, GitHub/ORCID public references and provenance; profile edits cannot write role/status/verified identity fields |
| Avatar asset | Managed storage key, media type, dimensions, checksum, source kind/revision/person mapping, owner, creation time; no raw external URL or image binary in user responses |
| EmailAddress | Canonical unique address, owner, primary/verified state; at most one primary per user |
| ExternalIdentity | Owner, provider, issuer, immutable subject, display metadata, linked timestamp; unique provider/issuer/subject |
| BrowserSession | Owner, unique secret digest, created/last-seen/absolute-expiry/revoked times, authentication/MFA times, non-secret device description |
| ApiKey | Fields and constraints from section 6; indexed owner and unique digest |
| AccountActionToken | Reuse or evolve existing purpose-bound tokens for reset, verification, invitation, and onboarding; explicit target account/email and expiry/consumption |
| Study grants | Effective curator assignments and read grants linked to stable user/study IDs; unique pairs; independent of replaceable scientific attribution |
| SecurityConfiguration | Singleton designated administrator ID and migration/cutover metadata |
| MFA credential | Administrator owner, encrypted TOTP seed, confirmation state, replay counter, hashed recovery codes |
| RoleRequest | Requester, reason, pending/approved/rejected state, decision actor/time; at most one pending request per user |
| AuditEvent | Actor ID, credential ID/kind, action, target ID, timestamp, request ID, outcome, allowlisted before/after changes; no credentials or whole request bodies |
| Usage counters and concurrency leases | Atomic shared counters by account/key/IP/class; expiring leases and retention cleanup |

Transient OAuth transactions must also be server-side, expiring, and single-use. Existing `Token` rows with purpose `api` are legacy credentials only; never reinterpret them as modern keys without a deliberate migration policy. Distinguish sessions, keys, and account-action credentials in validators so a token for one purpose cannot authenticate another.

Audit role/grant/status changes, key creation/rotation/revocation, provider linking, security recovery, administrative edits, and import results. Record key ID, never secret. Retain security audit events for 365 days by default; keep detailed usage for 30 days and avoid raw IP retention where aggregate or keyed identifiers suffice. Restrict account-level security history to its owner and authorized administrator.

## 8. HTTP and frontend contract

Add canonical endpoints under `/api/v1`. The table defines proposed route names and behavior; use shared services behind compatibility adapters.

| Method and path | Contract |
| --- | --- |
| `GET /auth/csrf` | Establish/return the CSRF challenge needed for browser mutations |
| `POST /auth/register` | Create pending ordinary account; generic acceptance response |
| `POST /auth/login` | Password authentication; establish session or MFA challenge, never return an API key |
| `POST /auth/logout` | Revoke current session and clear cookie |
| `POST /auth/reauthenticate` | Refresh authentication assurance; provider users can use a bound provider reauthentication flow |
| `POST /auth/verify-email`, `/auth/resend-verification` | Complete/resend contact verification |
| `POST /auth/request-password-reset`, `/auth/reset-password` | Generic request response; atomically complete reset and revocation |
| `POST /auth/invitations/accept` | Complete bound invitation with a password |
| `POST /auth/onboarding/invitation` | Complete the exact imported-account invitation using browser-bound proof of GitHub/ORCID ownership |
| `GET /auth/{provider}/start`, `/auth/{provider}/callback` | State-bound GitHub/ORCID login; link intent requires authenticated recent assurance and CSRF-protected initiation |
| `POST /auth/mfa/enroll`, `/auth/mfa/confirm`, `/auth/mfa/verify` | Enroll/confirm TOTP and complete MFA challenge; separately rate-limited recovery-code completion |
| `GET /me` | Profile, role, effective UI capabilities, onboarding/MFA state |
| `PATCH /me` | Update allowlisted display name, affiliation, title, and unlinked profile references; reject role, status, username, email, and authenticated-provider changes through this route |
| `PUT /me/avatar`, `DELETE /me/avatar` | Upload/replace or remove own avatar; return managed image URL or fallback |
| `GET /me/studies` | Paginated assigned studies |
| `GET /me/sessions`, `DELETE /me/sessions/{id}` | List/revoke own browser sessions |
| `GET /me/identities`, `POST /me/identities/{provider}/link`, `DELETE /me/identities/{id}` | List, initiate explicit linking, or safely unlink own identities |
| `GET /me/api-keys`, `POST /me/api-keys` | List metadata or issue one-time secret |
| `DELETE /me/api-keys/{id}`, `POST /me/api-keys/{id}/rotate` | Revoke or rotate own key |
| `POST /me/role-requests` | Request curator access |
| `GET /me/security-events` | Paginated own security history |
| `GET /admin/users`, `PATCH /admin/users/{id}` | Search/paginate users; update allowed role/status/profile fields |
| `POST /admin/users/{id}/invitations` | Issue/resend invitation without returning credentials |
| `GET /admin/role-requests`, `PATCH /admin/role-requests/{id}` | Review and resolve curator requests |
| `PUT /admin/studies/{sid}/access` | Explicitly update assignments, read grants, creator, visibility, or licence |
| `DELETE /admin/users/{id}/api-keys/{key_id}` | Revoke a user's key |
| `GET /admin/usage`, `GET /admin/audit-events` | Paginated usage and security visibility |

Existing email-address management can retain its routes but must use the new session/reauthentication policy. Vocabulary authoring and study deletion routes must apply administrator session assurance even if their URLs remain unchanged. Administrative list responses expose metadata, never password hashes, key digests, or MFA material.

Use `201` for resource creation, `202` for generic registration/recovery acceptance, and `204` for successful revocation. Use `401` for missing/invalid/expired/revoked credentials, `403` for insufficient privilege/scope/assurance, `404` for inaccessible study or other user's credential resources, `409` for identity/version conflicts, `422` for invalid fields, and `429` with `Retry-After` for throttling. Provide stable machine-readable error codes and request IDs. Compatibility adapters may retain legacy envelopes during the transition, with equivalent security behavior.

Account UI includes login/register, provider buttons, pending verification, invitation acceptance, recovery/MFA, profile/providers, sessions, keys, assigned studies, and curator requests. Administrator UI includes searchable users, role/status changes, assignments, invitations, requests, usage, and audit history. UI controls reflect capabilities, but backend checks are authoritative. Never offer `admin` in a role selector.

## 9. Rate limits and overload protection

API keys identify traffic; they do not prevent overload without enforcement. Keep public interactive reads available with conservative anonymous limits. Require authentication for bulk exports and personal keys for unattended API/MCP clients. Browser cookies are not proof of human traffic and receive account quotas too. Do not rely on User-Agent, robots.txt, or hidden routes for protection.

Apply atomic shared limits across all workers, REST/MCP transports, and every key/session of the same account. Add per-key and per-IP buckets; multiple keys cannot multiply an account's allowance. Only trust forwarding headers from configured reverse proxies. Use PostgreSQL counters/leases initially; add another service only if measured contention requires it. Expiring concurrency leases must recover from crashed workers. Limiter failure returns a controlled `503` for expensive operations rather than permitting unbounded work.

Initial configurable defaults below are starting values, not measured capacity promises. Verify and tune them with representative queries/uploads before production rollout. Role does not imply unlimited capacity; administrator-approved quota overrides are explicit and audited.

| Limit | Initial default |
| --- | --- |
| Anonymous read requests | 30/minute per source IP |
| Authenticated ordinary requests | 120/minute per account; 60/minute per key; additional configurable IP ceiling of 600/minute |
| Concurrent reads | 2 per anonymous IP; 6 per account |
| Expensive queries/exports | Authenticated only; 10/minute and 1 concurrent per account |
| Upload/validation | 10/hour and 1 concurrent per account; 2 concurrent globally |
| Login attempts | 10 per account identifier and 30 per IP per 10 minutes |
| Registration/email sends/recovery | 3/hour per canonical address and 20/hour per IP |
| MFA verification | 5 per pending challenge/account per 10 minutes, plus IP ceiling |

Set explicit global caps for expensive reads, query duration, response/download bytes, upload body size, expanded archive size, and page size from existing limits and load-test evidence; deployment documentation must state actual values before enabling production access. Classify routes/tools centrally so changing transport cannot evade an expensive-operation limit. Cache only public responses without mixing authenticated/private representations. Public dataset snapshots provide the preferred bulk-data path and require their own bandwidth protection.

Expose request counts, rejection counts, expensive-operation duration, active work, and usage by account/key to the administrator. Alert on sustained global saturation and unusual authentication failures. Backups must include account/security data and required encryption-key recovery procedures without putting operational secrets in repository files.

## 10. Existing curator and reviewer migration

### 10.1 Authoritative initial roles

Use the existing curator roster defined in the user-specified `users.py` as the source for initial curator population. Apply these explicit overrides when building the reviewed import:

| Existing identity | Initial role |
| --- | --- |
| `USERNAME` | `admin` (sole administrator; provision through the dedicated command) |
| Mariia Myshkina | `reviewer` |
| Michelle Elias | `reviewer` |
| Shubhankar Palwankar | `reviewer` |
| Other curators defined in the existing `users.py` roster | `curator` |
| New registrations and accounts without an explicit privileged assignment | `user` |

Resolve the three named reviewers to their exact existing usernames/internal IDs in the import manifest; the names above are requirements, not a fuzzy matching rule. Apply precedence `USERNAME` administrator designation, then the three reviewer overrides, then roster curator assignments, then the ordinary-user default. Do not derive roles from a model default, an uploaded study's contributor list, or provider claims. Initial role assignment does not bypass invitation, identity verification, or suspension rules.

Resolved source: `backend/pkdb_data/management/users.py` at PK-DB revision `632a8bb21a894e97e2a4f6df7173f0956ded09f5`, recorded in `backend/bootstrap/curator-roster.json`. Its 69 historical accounts map Mariia Myshkina to `MariiaMysh`, Michelle Elias to `mii-halina`, and Shubhankar Palwankar to `shubhankarpalwankar`. The historical `reviewer` test account is excluded; `USERNAME` is handled by administrator bootstrap. The importer preserves separate identities for the reviewed duplicate candidates `deepa`/`DeepaMahm` and `long231a`/`lucialink30` pending explicit operator resolution. Do not substitute the empty `backend/bootstrap/users.json` for this roster. Include the resolved source path/revision and exact account mappings in the dry-run report.

These are initial migration assignments, not recurring synchronization rules. Later administrator changes remain authoritative; rerunning the import must not restore a removed curator/reviewer role.

### 10.2 Import and account activation

Provide `pkdb import-users PATH --dry-run` and an explicit apply mode. The input is a private, schema-validated JSON/CSV roster containing existing username, trusted contact email, desired role (`user`, `curator`, or `reviewer`), optional explicit existing user ID, and assigned study IDs. Provision the administrator through the dedicated command. Store no passwords, API keys, or private roster in Git. Provider identifiers in source data are attribution only until ownership is authenticated.

The dry-run report shows create/match/conflict operations, assignment changes, missing studies, reserved usernames, duplicate addresses, and current/proposed roles. Do not match privileged accounts by fuzzy names or public provider handles. Require explicit resolution of ambiguous identity matches before applying. Keep import provenance and a content digest so rerunning the same input is idempotent.

Apply a reviewed roster transactionally. Preserve existing IDs, study attribution, password hashes, verified addresses, and valid credentials unless the transition policy requires revocation. Do not overwrite a differing role or grant silently: changed existing records require an explicit reviewed update mode. Never reactivate suspended users or reverse a later administrative demotion on a routine rerun. Historical contributor-only accounts stay disabled. Study corpus imports never create active privileged users.

For existing creators who need continued curator access, materialize explicit curator assignments from the reviewed migration mapping; do not retain implicit creator write privileges. Assign reviewer roles only where explicitly listed. Export pre-migration relationships and compare them to the post-migration report.

Users lacking usable credentials receive an invitation bound to the existing account and reviewed contact address. Invitation completion activates that account, sets a password or links a proved external identity, and retains its assignments. It must not create a duplicate account. If no trusted address exists, leave the identity disabled until the administrator verifies ownership. Queue/send invitations only through an explicit operator action after the import succeeds, with delivery/retry status and no secrets in reports.

## 11. Rollout and compatibility

1. Back up the database, inventory existing accounts/tokens/grants, and run the import/migration dry run. Confirm the designated `USERNAME` identity and resolve conflicting administrators.
2. Deploy additive schema changes and centralized authorization. Backfill explicit assignments before removing implicit creator writes. All old and new endpoints immediately use the corrected role matrix.
3. Deploy browser sessions, MFA, key management, shared quotas, and frontend changes. Remove local-storage token use and make logout server-side. Existing users sign in again to establish browser sessions.
4. Enable GitHub and ORCID after callback and sandbox/production smoke tests; then enable public registration and issue reviewed invitations.
5. Allow pre-cutover legacy API tokens for at most 30 days or their earlier existing expiry. Give them an explicit legacy credential kind with only `read` and `studies:write`, further restricted by current role and assignments. Legacy credentials never grant account or administrator operations. Apply the same quotas, suspension checks, revocation, and per-request authorization.
6. Stop issuing legacy tokens at cutover. `/api-token-auth/` returns a documented migration response (HTTP `410`) directing scripts to personal keys and browsers to session login. Temporarily accept `Authorization: Token` only for existing legacy credentials. Return deprecation/sunset metadata and publish the exact cutoff date in release/deployment documentation.
7. Revoke remaining legacy credentials at the persisted cutoff and remove compatibility support in a subsequent release. Restarting the application must not extend the window. Verify that `pkdb` uploads and existing automation have replacement keys before sunset.

Rollback may disable new registration/providers while retaining existing sessions/keys and migration data. Do not roll back to authorization that restores removed privileges, drops new account records, or revives revoked tokens. Test restoration on a disposable database; never use production volumes for migration tests.

## 12. Implementation sequence

| Stage | Deliverables | Exit condition |
| --- | --- | --- |
| 1. Permissions and schema | Role defaults/matrix, grant separation, scoped principals, designated administrator, migrations | Role/assignment and ingestion authorization tests pass; existing account IDs preserved |
| 2. Accounts and browser security | Session cookies, CSRF, recovery/invitations, MFA, account/admin UI | Complete browser lifecycle works without local-storage credentials |
| 3. Keys and quotas | Key lifecycle/UI, REST/MCP scopes, shared throttles, usage/audit views | Scripts work with keys; revocation and quota bypass tests pass |
| 4. Providers and migration tooling | GitHub/ORCID, safe linking, roster dry-run/apply, invitation delivery, curator requests | Existing curator/reviewer account can be claimed without losing study relationships |
| 5. Cutover | Deployment documentation, measured limits, compatibility sunset, recovery rehearsal | Acceptance suite and operational smoke tests pass |

Commit migrations, lockfile changes, configuration examples without secrets, operator documentation, frontend/API changes, and meaningful tests in reviewable increments. Run the repository-required tests, Ruff, ty, and documentation checks for the implementation. This document alone does not require application behavior changes.

## 13. Acceptance criteria

### Permissions and data integrity

- A normal registrant cannot choose a role or upload studies. A curator can create a private study and becomes assigned to it.
- Curator A can edit assigned study A but cannot validate, replace, attach files to, or delete unassigned study B. Spoofing the creator, uploader, or curator names in a payload does not change that result.
- A reviewer can read and edit every public/private study without an assignment, but cannot change vocabulary, assignments, visibility, licence, ownership, roles, or delete studies.
- Only the designated `USERNAME` administrator can perform administrative actions, using a fully authenticated session. An administrator-owned API key cannot do so.
- Demotion to ordinary user removes writes even when the user remains a creator or assigned curator. Assignment removal removes a curator's writes. Transactional race tests cover writes concurrent with role/grant changes and credential revocation.
- Replacement preserves effective grants and rejects unauthorized protected-field changes without partial publication. Scientific author/curator attribution remains intact through migration.
- Search, pagination totals, exports, file access, and MCP do not leak private data. Existing licence restrictions remain effective.

### Credentials and accounts

- Registration requires only username, primary email, and a password for password-based signup. Display name and all other profile fields remain optional; missing photos receive a local fallback.
- Primary and secondary email verification, promotion/removal, uniqueness, and recovery work without exposing either address in public responses. Pending address changes preserve the previous verified primary address. Administrator recovery still requires MFA assurance.
- The reviewed roster includes 46 site-avatar mappings (45 distinct images), two existing PK-DB photos, and 21 fallback entries including the excluded test account. Mapped images import to the correct accounts; unmapped identities use fallbacks. Imported avatars work without the sibling repository at runtime, and repeated imports preserve user edits and explicit removals.
- Avatar upload rejects excessive size/dimensions, misleading media types, SVG, and animation; generated files contain no source metadata. Free-text profile fields are escaped and cannot modify permissions.
- Imported/self-asserted GitHub and ORCID references cannot authenticate, link accounts, acquire a verified badge, or change roles without the provider ownership flow. Public profile serialization excludes emails, credentials, and private study relationships.
- Pending and suspended accounts cannot create usable sessions/keys through any login, verification, reset, invitation, or provider flow.
- Session logout, idle/absolute expiry, CSRF checks, cookie attributes, reauthentication, MFA replay prevention, and single-use recovery codes are tested.
- Password reset revokes sessions and keys. Suspension blocks all providers and credentials; reactivation never revives them.
- Secrets appear only at deliberate issuance/delivery and are absent from stored plaintext, list responses, logs, telemetry, and frontend persistence.
- A read-only key cannot write; a curator write key cannot edit an unassigned study; a reviewer write key can edit all studies. Tests exercise both REST and MCP and prevent scope loss during service calls.
- Rotation respects overlap/expiry; revocation is idempotent; concurrent creation cannot exceed the active-key limit. Keys cannot create keys or administer accounts.
- OAuth state/PKCE and OIDC validation failures reject login. Provider ID uniqueness and concurrent linking are tested. Matching email/username alone never links identities or grants privileges. ORCID registration works without a provider email.
- Invitations activate the intended existing account exactly once. Link scanners, replayed tokens, wrong-purpose tokens, expired tokens, and concurrent redemption cannot take over accounts.

### Migration, operations, and overload

- Import dry runs make no changes and expose conflicts. Repeated imports preserve credentials and do not revive suspended accounts or undo later role changes. No private roster or secrets enter Git.
- The resolved `users.py` roster populates existing curators, with Mariia Myshkina, Michelle Elias, and Shubhankar Palwankar mapped to their verified existing identities as reviewers. `USERNAME` remains the sole administrator, and new registrations default to `user`. Missing or ambiguous roster/reviewer identities block import application and appear in the dry-run report.
- `USERNAME` is reserved before registration, adopted only through explicit bootstrap, and is the sole administrator under concurrent operations.
- Legacy credentials expire at the fixed cutoff, cannot access management endpoints, and follow current roles/scopes/quotas throughout transition.
- Multi-worker tests prove account quotas are shared across keys, sessions, REST, and MCP. Creating more keys does not increase allowance. Proxy-header spoofing cannot bypass IP limits.
- Limits cover expensive queries, uploads, pagination, exports, and downloads. Crashed workers release concurrency capacity through lease expiry. `429` includes a meaningful retry interval.
- A full curator journey succeeds: invitation → login/provider link → view assignments → create scoped key → upload assigned study → rotate key. A reviewer journey edits an unassigned private study. Administrator recovery is rehearsed on a disposable environment.

## 14. Provider references

- [Authlib OAuth clients and framework integrations](https://docs.authlib.org/en/stable/oauth2/client/)
- [GitHub authorization-code flow and PKCE](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
- [GitHub stable identity and OAuth best practices](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/best-practices-for-creating-an-oauth-app)
- [ORCID authenticated iD and OpenID Connect tutorial](https://info.orcid.org/documentation/api-tutorials/api-tutorial-get-and-authenticated-orcid-id/)
- [ORCID integration and API FAQ](https://info.orcid.org/documentation/integration-and-api-faq/)

Verify provider configuration and supported protocol details against these official references when implementing and before production activation.
