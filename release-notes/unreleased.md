# Unreleased

- Document the minimal local Docker setup, administrator and attribution accounts, and study upload through the `pkdb` Python package.

- Show vocabulary resource names alongside external annotation links and resolve legacy URL placeholders using term identifiers.

- Display a large PK-DB logo beside the landing-page heading, with responsive sizing and a contrasting background in dark mode.

- Name the Pharmacokinetics Database prominently on the landing page and enable reliable Docker frontend hot reload with configurable polling, and document the live development workflow.

- Publish Terms of Use in the documentation with required source citation, coauthorship for reuse of more than 10 studies, and commercial data licensing; update site links and the terms bundled with data exports.

- Simplify the landing page to mission, vision, and live database statistics; move the example study and citation information into documentation. Promote API to top-level navigation and show contact and issue reporting links in shared frontend and documentation footers.
- Report actionable `create-admin` errors for existing administrators and invalid input without exposing passwords or database credentials.
- Search vocabulary while typing, copy exact curation names with one click, and show annotations, cross-references, units, and parents in a compact table.
- Allow negative values for all change measurements in server and Python client validation, including absolute, relative, and derived changes; baseline measurement restrictions remain unchanged.

- Add a GitHub issue reporting link to desktop and mobile navigation, and use `PKDB_ADMIN` and `PKDB_ADMIN_EMAIL` placeholders in administrator setup documentation.
- Run regular Python CI on Linux with Python 3.14; reserve the complete Python and operating-system matrix for release tag pushes.

- Show the frontend release version, linked build commit, and Matthias König copyright and group link in the shared footer on every page.
- Replace the frontend and documentation branding and favicons with the new PK-DB logo.
- Start documentation with Introduction and Webinterface, and place Accounts and API keys before REST API and Python client.
- Allow authorized API-key uploads to create public or private studies and change visibility on replacement. Restrict private-study access to explicitly assigned curators and administrators; creator attribution, collaborator assignments, and reviewer status alone no longer grant access.
- Show server validation details in Python client and CLI HTTP 422 errors.
- Update upload and access documentation, and exclude internal specifications, plans, and migration records from documentation search.
- Simplify browser login to username and password. Remove GitHub/ORCID authentication and administrator MFA, retaining editable optional GitHub/ORCID profile fields. Add `pkdb create-user` for active local accounts without SMTP or email setup. Apply the authentication cleanup migration when upgrading; provider-only accounts need a password reset.
