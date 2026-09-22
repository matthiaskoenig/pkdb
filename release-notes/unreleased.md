# Unreleased

- Move vocabulary authoring to `backend/info_nodes`, reuse pymetadata annotations, and index node relationships for generation. Normalize description formatting and record curation diagnostics in provenance.
- Upgrade to pymetadata 0.6.5, resolve BioRegistry and SIO/OBI metadata, restore missing offline ontology records, and correct the macroalbuminuria SCDO identifier.
- Remove the outdated API example notebook.
- Modernize the frontend to Vue 3, Vuetify 4, Pinia, Vite, and strict TypeScript with a reproducible npm lockfile. Remove the Vue 2 plugin, Vuex, Vue CLI, and unused Vega stacks.
- Add explicit draft/applied researcher searches, shareable criteria, clearer selection scopes, scientific tables, lazy plots, accessible mobile filters, and applied-dataset exports. Preserve account, administration, vocabulary, and authenticated file workflows.
- Add isolated PostgreSQL/browser acceptance coverage and make frontend validation a release requirement.
