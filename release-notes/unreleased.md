# Unreleased

- Add permission-filtered `/api/v2/statistics` coverage metrics and interactive landing-page charts for studies, substances with timecourses, and reported/calculated PK parameters by study year. Include cumulative views, year and parameter filters, current substance coverage, accessible data tables, and explicit undated totals (#767).

- Make flat study analysis apply related measurement filters to the same measurement, matching normal study queries.
- Retire legacy study/reference drafts, attachment-handle upload routes, and index finalization. Use complete-bundle uploads through `PUT /api/v2/studies/{sid}`. Migration `p002retirelegacy` preserves published studies and attachments but removes pending legacy drafts and ineffective reader grants; downgrade restores their schema, not discarded data.
- Remove ineffective reader assignment controls and unused authenticated quota settings, usage reporting, and MCP quota bookkeeping. Curator assignments and collaborator attribution retain their existing meanings.

- Unify groups and individuals as subjects and characteristics and outputs as observations. Share reported/normalized context and intervention links, and replace timecourse/scatter point tables with ordered dataset arrays. Consolidate migration history into `p001initial` for an empty database and fresh study uploads; historical database upgrades are no longer supported. Use a processing-version-6 client. Characteristics and outputs now share count defaults and statistical completion.

- Add `pkdb curation`, a local browser interface with GitHub assignment selection, default-application file opening, validation or upload on save, detailed diagnostics, and explicit recovery for uncertain uploads. Include an authenticated read-only curation-context endpoint and documentation with screenshots.

- Remove authenticated-user request and concurrency throttling, allow normal anonymous browsing bursts, expose Docker anonymous quota settings, and show retry delays for frontend quota errors.

- Add readable study upload progress and atomic batch reports to `pkdb`, negotiated backend diagnostics with correction guidance and save outcomes, and accurate physical spreadsheet cell locations.

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
- Simplify browser login to username and password. Remove GitHub/ORCID authentication and administrator MFA, retaining editable optional GitHub/ORCID profile fields. Add `pkdb create-user` for active local accounts without SMTP or email setup. Fresh installations include the simplified authentication schema.
