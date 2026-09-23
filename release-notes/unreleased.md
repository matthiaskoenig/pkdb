# Unreleased

- Show the frontend release version, linked build commit, and Matthias König copyright and group link in the shared footer on every page.
- Replace the frontend and documentation branding and favicons with the new PK-DB logo.
- Start documentation with Introduction and Webinterface, and place Accounts and API keys before REST API and Python client.
- Allow authorized API-key uploads to create public or private studies and change visibility on replacement. Restrict private-study access to explicitly assigned curators and administrators; creator attribution, collaborator assignments, and reviewer status alone no longer grant access.
- Show server validation details in Python client and CLI HTTP 422 errors.
- Update upload and access documentation, and exclude internal specifications, plans, and migration records from documentation search.
- Simplify browser login to username and password. Remove GitHub/ORCID authentication and administrator MFA, retaining editable optional GitHub/ORCID profile fields. Add `pkdb create-user` for active local accounts without SMTP or email setup. Apply the authentication cleanup migration when upgrading; provider-only accounts need a password reset.
