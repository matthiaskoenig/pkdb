# Account administration

!!! important "For developers and operators only"

    This section is for working on PK-DB itself or running a separate server. General users do not need a source checkout, Docker, a database, or administrator access. To use PK-DB, start with [Browse and access data](web-interface.md) or the [Python client and API](python-client.md).

Operator commands below act on the server selected by its environment. For the local Docker stack, use `docker compose exec backend pkdb-server …` in place of `uv run --project backend pkdb-server …`.

## Local development accounts

After applying migrations, create an active account with a password:

```bash
uv run --project backend pkdb-server create-user developer
```

The command prompts for a password; it needs no email, mail server, external provider, or authenticator. Use `--role curator --email developer@example.org` for local API-key upload testing or `--role reviewer` to test reviewer access. API-key creation requires a verified primary contact; the operator-supplied `--email` creates that contact without mail delivery. For browser login, email is optional; `--password-stdin` supports scripted provisioning without placing the password in command arguments. Existing identities are not overwritten. Sign in using the new username and password.


## Administrator bootstrap

Replace `USERNAME` and `ADMIN_EMAIL` with your chosen username and email. Apply migrations before provisioning accounts. From the repository root, with deployment environment variables set:

```bash
uv run --project backend pkdb-server create-admin USERNAME --email ADMIN_EMAIL
```

The command prompts for a password. For a reviewed existing active account, use its exact internal ID instead; adoption preserves its password:

```bash
uv run --project backend pkdb-server create-admin USERNAME --email ADMIN_EMAIL --adopt-user-id EXISTING_ID
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
uv run --project backend pkdb-server import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --dry-run
```

The private contact overlay is a JSON list or CSV with `username`, optional `email`, optional exact `user_id`, and optional `assigned_study_ids`. Study IDs are internal positive integer IDs; CSV study IDs use semicolons. Keep contacts out of the public repository. Supply only reviewed addresses and explicit account/study mappings. For example:

```json
[
  {"username": "MariiaMysh", "email": "reviewed-contact@example.org", "user_id": 42, "assigned_study_ids": [123]}
]
```

Apply only after resolving dry-run conflicts:

```bash
uv run --project backend pkdb-server import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --apply
```

Changes to existing roles or explicit grants require `--update-existing`; add it to both preview and apply after reviewing the proposed differences. A conflicting primary address requires separate resolution. `--avatar-root` defaults to `frontend/public` and must contain the manifest's `assets/images/avatars/` paths. In a backend-only container, mount those assets and pass the corresponding root explicitly.

Dry runs create no accounts or asset files. Applying preserves existing IDs, credentials, suspension and user edits. New imported identities remain disabled. Matching import digests become no-ops, so rerunning the same manifest does not undo a later demotion or cleared photo. Invitations are a separate authenticated administrator action in **User administration → Invite**, or through `POST /api/v1/admin/users/{id}/invitations` with a reviewed `email_id`. The dialog shows the reviewed primary contact and requires an explicit send; failures allow a retry. Unclaimed accounts cannot be activated instead of completing verification. Acceptance claims that identity without changing its assigned role. Imported GitHub/ORCID references are public metadata, not sign-in credentials.


## Maintenance

Run `pkdb-server cleanup` regularly to remove unreferenced avatar files after their grace period, expired credentials and leases, and old audit events. Back up the database and managed files together; see [Deployment](deployment.md).
