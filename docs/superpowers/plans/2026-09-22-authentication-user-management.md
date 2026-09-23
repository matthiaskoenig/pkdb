# Implementation plan for #775

Specification: [Authentication, user management, and API keys](../specs/2026-09-22-authentication-user-management-design.md). Started 2026-09-22. User authorized planning and implementation. Checkboxes track delivered and verified work, not intended functionality.

## Work packages

1. [x] Recover the historical `users.py` roster, resolve reviewer identities, audit every curator against `livermetabolism-site`, and add a non-secret identity/avatar manifest with copied matching thumbnails. Document unmapped identities explicitly.
2. [x] Centralize the corrected role matrix: ordinary-user defaults, assigned-only curator writes, global reviewer writes, administrator-only protected operations. Preserve effective grants through study replacement and migrate existing creator grants explicitly. Test through API/service entry points and recheck authorization on commit.
3. [x] Add minimal profile persistence, safe public/private serializers, profile editing, validated avatar upload/removal, and profile migration. Keep provider references separate from authenticated identities and email addresses in the existing verified-address model.
4. [x] Add managed browser sessions, CSRF/origin protection, recent authentication, administrator designation/MFA and audited recovery. Integrate frontend sign-in, logout, profile, and account settings without local-storage credentials.
5. [x] Implement personal key lifecycle, scopes, immediate revocation, rotation, REST/MCP enforcement, shared account quotas, and security/usage audit views. Preserve credential restrictions at service boundaries.
6. [x] Implement GitHub/ORCID authorization-code sign-in and explicit account linking with bounded server-side onboarding. Add provider configuration, failure handling, ownership verification, and tests.
7. [x] Implement reviewed dry-run/apply user import, assignment population, invitations, administrator user/role/access management, and curator requests. Import avatars/profile references without overwriting user changes or enabling unverified logins.
8. [x] Deliver frontend account/key/admin workflows, deployment configuration, legacy-token transition with a fixed sunset, operator documentation and recovery instructions. Verify curator/reviewer workflows through automated HTTP integration tests and required repository checks. Connected-browser visual QA and deployment checks remain explicit release gates below.

## Execution and ownership

Follow `/home/USERNAME/AGENTS.md` and `CLAUDE.md`. Use parallel agents for independent roster/avatar work and profile implementation while the primary agent owns authorization, integration, and this plan. Coordinate shared user-model and migration changes before edits. Use the disposable database in `compose.test.yaml`; never migrate the live deployment while implementing. Keep production provider credentials, roster contact addresses, invitations, and delivery out of source changes.

## Verification

Run meaningful permission regressions before changing authorization, then run targeted unit/API/integration tests for each package. Exercise pending/suspended accounts, wrong-purpose tokens, privilege downgrade, scope preservation, unauthorized study access, protected-field replacement, concurrent credential/grant changes, unsafe avatar input, and import idempotency. Use actual PostgreSQL migrations and transaction behavior. Run the complete backend suite, Ruff, ty, documentation build, frontend build and browser smoke checks before claiming implementation complete. Record external setup dependencies and outstanding work rather than marking unverified stages complete.

## Progress and evidence

- Initial checkout contained only the new specification as an untracked user-authorized document; no pre-existing implementation edits.
- Located the historical roster in Git at `a4e743bd^:backend/pkdb_data/management/users.py`. Resolve exact identities from that source, rather than guessing from display names.
- Recovered all 69 historical accounts: 46 mapped to 45 site thumbnails, two existing PK-DB images retained, 21 explicit fallbacks including the excluded historical test account. Exact reviewers are `MariiaMysh`, `mii-halina`, and `shubhankarpalwankar`. The manifest validator checks roles, paths, and checksums.
- Implemented separate effective study grants and preserved existing relationships through migration. Reproduced reviewer upload rejection through the HTTP upload endpoint before fixing the role matrix; regressions cover reviewer global writes, curator demotion, grant removal, upload-driven grants, and administrator-key attempts to change protected metadata.
- Implemented minimal profiles, locally managed avatars, cookie/CSRF sessions, administrator TOTP/recovery, scoped keys, explicit provider identity linking, verified provider onboarding, invitations, roster import, role requests, and administrator access management.
- Implemented shared PostgreSQL request counters and expiring concurrency leases for HTTP requests and individual MCP tool operations. MCP streaming transport connections are not counted as tool operations. Added cleanup of expired credentials, OAuth transactions, leases/counters, old audit events, and orphan avatar files.
- Frontend account workflows use cookie sessions and no persistent bearer tokens. Production build and four frontend authentication tests passed. Replaced unsupported node-sass with Dart Sass for the Node 22 build.
- Security review fixed credential restrictions being lost during exports and staged-file access, required verified contact preservation, and sanitized canonical account validation errors to avoid echoing secrets.
- Authlib's Requests adapter is used. Automatic dependency review rejected adding the alternative HTTP client, so provider implementation was changed to the supported Requests integration. No blocked dependency installation remains necessary.
- Changes are on `feat/775-authentication-user-management`; no production migration, account activation, invitation delivery, provider-account authorization, or deployment was performed.


## Release and follow-up gates

- Configure the public HTTPS origin, SMTP, persistent MFA encryption key, GitHub OAuth app, and ORCID client in the deployment environment. Actual provider callbacks and delivered email must be checked with those credentials on staging.
- Run connected-browser desktop/mobile visual QA. The available browser runtime returned no browser connection during implementation; production compilation and component tests do not substitute for this check.
- Benchmark the configured budgets against representative production data before release. Current counters/leases enforce bounded requests; dedicated query-cost weighting, persistent historical usage analytics, per-account quota overrides, and saturation alerts remain follow-up operational work.
- Invitation delivery is synchronous with explicit retries; a durable mail outbox is not implemented. Password and browser-bound GitHub/ORCID invitation claiming are supported.
- Automatic dataset snapshot publication remains follow-up product work. Primary-address change notifications are implemented with rollback on delivery failure; registration reserves `USERNAME`. Database uniqueness constraints protect case-insensitive usernames and primary email selection; migration preflight reports conflicting legacy identities instead of merging them.
- Do not deploy or declare all specification acceptance criteria met until the outstanding staging and operational checks are resolved. The implementation is a reviewable first delivery of #775, with the above gaps explicit.

## Verification results

- HTTP authorization regression reproduced before the permission fix, then passed for assigned curators, global reviewers, demotion, effective-grant preservation, and protected metadata.
- Targeted MFA/quota/management/cleanup checks: eight tests passed, including MFA replay/recovery, shared account budgets, crashed-lease expiry, role approval, HTTP throttling, secret-safe validation, and avatar/credential cleanup integration.
- Frontend production build, four frontend authentication tests, and changed-file ESLint passed. No connected browser was available for visual QA.
- Repository Ruff, formatting, ty, diff checks, roster validator, and clean documentation build passed. Complete PostgreSQL backend and migration-tool suite: **446 passed** in 119.86 seconds, with one upstream Starlette/AnyIO deprecation warning. This includes the final uniqueness migrations and concurrent MCP principal-isolation regression.

## Follow-up implementation plan

The next pass completes core account journeys that were only partially exposed in the first delivery. Production credential setup and live staging checks remain external release gates.

1. [x] Expose reviewed primary-contact metadata and invitation eligibility to the administrator; add explicit invitation delivery with success/failure feedback in user management. Preserve inactive/suspended distinctions and never offer activation as a substitute for verification. Reactivation requires a verified matching primary contact even after suspension clears pending state; HTTP regressions cover both password and provider identities.
2. [x] Allow a user who has proved a new GitHub/ORCID identity to submit their invitation token and claim the exact imported account without choosing a password. Bind the proof to the browser, consume the invitation once, reject collisions/suspension, and preserve role and study assignments.
3. [x] Add assigned-study navigation and personal security-event history to account settings, using the existing authorized endpoints.
4. [x] Let users hide public GitHub/ORCID references while retaining their connected sign-in methods.
5. [x] Test invitation eligibility/delivery and provider claiming through HTTP/integration tests, test the new frontend workflows, then run required backend, frontend, type, lint, roster, and documentation checks. Record remaining browser/staging limitations explicitly.

### Follow-up verification results

- Final complete PostgreSQL backend and migration-tool suite: **460 passed** in 134.80 seconds, with one upstream Starlette/AnyIO deprecation warning. Includes GitHub/ORCID invitation claims, browser binding, identity collisions, verified-contact activation enforcement, profile visibility, and historical migration preflight.
- Frontend: **13 tests passed**, production build and changed-file lint passed. Tests cover invitation delivery/retry, passwordless claiming, activity pagination/account changes, and privacy preference persistence.
- Ruff, formatting, backend type checks, diff checks, roster validation, and documentation build passed.
- Browser connection was retried using the browser skill; discovery returned no available browsers. Live provider/SMTP and desktop/mobile visual QA remain release gates, alongside the operational follow-ups already listed above.

### Pull-request compatibility checks

- Updated Compose CI to bootstrap the designated administrator and verify cookie/CSRF login, administrator MFA gating, and the retired token endpoint.
- Fresh installed-container smoke passed for personal key creation, REST study uploads/read/attachments, MCP access, and graceful shutdown.
- Reproduced and fixed the CLI sending new personal keys under the legacy authorization scheme. CLI/HTTP regression suite: 14 passed, covering browser-issued personal keys and legacy compatibility. Updated installation/local-upload instructions for administrator MFA and API key issuance.
