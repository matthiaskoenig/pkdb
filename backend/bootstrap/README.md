# Generated vocabulary

The authoritative editable definitions are in `../pkdb_data/info_nodes/definitions/`. Do not edit `vocabulary.json` or `provenance.json` manually. Regenerate them from the repository root with:

```bash
uv run --project backend --python 3.14 python scripts/update_vocabulary.py
```

Use `--check` to detect stale generated files. See [the vocabulary guide](../../docs/vocabulary.md) for authoring, cached metadata, and loading updated terms into Docker.

`users.json` is maintained separately and is not changed by generation. Compose loads the vocabulary automatically at startup. `pkdb bootstrap-study PATH` prepares disabled attribution accounts without changing existing credentials or roles.

## Curator roster and avatars

`curator-roster.json` records all 69 historical accounts from
`backend/pkdb_data/management/users.py` at the exact revision in the manifest.
It contains public identity mappings and intended migration roles, with no email
addresses or credentials. It is **not** an input to the existing account bootstrap.
The private invitation import must match existing account IDs/usernames explicitly,
review role changes, preserve suspension and user profile edits, and use separately
verified contacts. Site GitHub/ORCID references do not prove account ownership.

- `mkoenig` is the sole administrator, provisioned by administrator bootstrap.
- `MariiaMysh`, `mii-halina`, and `shubhankarpalwankar` are reviewers.
- Other historical curators remain curators, including former administrator `janekg`.
- Historical `reviewer` is a test account and is excluded from invitation import.
- `deepa`/`DeepaMahm` and `long231a`/`lucialink30` need manual duplicate review;
  the manifest preserves separate usernames and never merges account IDs.

All accounts were checked against `livermetabolism-site/data/people.yml`.
46 accounts have matched site avatars (45 distinct images). Exact source revision,
person ID, relative source filename, and SHA-256 are recorded. Matched WebP thumbnails
are copied to `frontend/public/assets/images/avatars/curators/`, so production does
not need the sibling repository. Existing PK-DB images are retained for `kgreen`
and `xresearch`. The other 21 entries, including the excluded test account, use
initials or a generic fallback; their missing mappings are explicitly recorded.
No remote avatar lookup or email hashing is needed.

Validate role invariants, local image availability, checksums, and absence of
private contact fields with:

```bash
python3 scripts/check_curator_roster.py
```

When refreshing images, explicitly review identity mappings and source revisions.
Never overwrite avatars users have replaced or removed. Historical spelling/name
variants remain as attribution names in this manifest; optional profile changes
can be made by users after account recovery.

### Operator commands

Set the usual `PKDB_DATABASE_URL` and `PKDB_FILE_ROOT` deployment configuration.
Provision/designate `mkoenig` first, so the roster can import the administrator's
profile and avatar without changing credentials or privileges. An undesignated
administrator row is skipped explicitly. Preview the public roster with optional
private contacts before applying:

```bash
pkdb import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --dry-run
pkdb import-users backend/bootstrap/curator-roster.json --contacts /private/contacts.json --apply
```

The contact overlay is a JSON list (or CSV) containing `username`, optional `email`,
optional exact `user_id`, and optional `assigned_study_ids`. CSV study IDs use
semicolon separation. Contact overlay usernames must already exist in the input
roster. An existing account whose role or explicit study grants would change
requires `--update-existing` after reviewing the dry-run conflicts. A conflicting
primary email requires separate review; the importer never replaces it. The
report contains contact availability, never contact addresses or credentials.

`--avatar-root` points to a directory containing `assets/images/avatars/` and
defaults to `frontend/public`. The importer verifies checksums and image content,
then copies avatars into managed backend file storage. Dry runs do not create
accounts, files, or import ledger records. Applied content digests make repeated
imports no-ops, preserving subsequent demotions and profile edits. New identities
remain disabled; invitations are a separate explicit administrator action.

Only `mkoenig` may be provisioned as administrator. For a new identity:

```bash
pkdb create-admin mkoenig --email ADMIN_EMAIL
```

The command prompts for a password. For the existing active identity, explicitly
supply its internal ID to preserve credentials:

```bash
pkdb create-admin mkoenig --email ADMIN_EMAIL --adopt-user-id EXISTING_ID
```

Adoption never reactivates a disabled/suspended account. The database migration
rejects multiple legacy administrators: review and reconcile legacy roles before
applying it. The designated identity is persisted by internal ID.

Offline MFA recovery requires operator database access and explicit confirmation:

```bash
pkdb recover-admin-mfa mkoenig --user-id DESIGNATED_ID --confirm-recovery
```

This clears administrator MFA enrollment, revokes all sessions/API keys/action
tokens, and records an audit event. It preserves identity, password, account state,
and role. The administrator must sign in and enroll MFA again before performing
administrator actions. It does not bypass account suspension or reset a password.

The final identity migration also rejects case-insensitive username duplicates
and accounts with multiple primary email addresses. Resolve those conflicts
through an explicit operator review before retrying the migration; it never
merges accounts, renames users, or chooses a primary email automatically.
The importer reports case-only username collisions and requires the exact
existing username/internal ID instead of guessing which account was intended.
