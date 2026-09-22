# Current backend runbook

Use [Installation](../installation.md) to start the current Docker stack and [Local upload testing](../local-upload-testing.md) to prepare attribution accounts, validate a study, upload it, and inspect the result.

For native development and schema changes, use [Development](../development.md). For storage and backup requirements, use [Deployment](../deployment.md).

The root Compose project is `pkdb-current`; it creates separate database and attachment volumes. It does not reuse historical deployment volumes. Historical migration reports remain evidence only; see [Migration records](README.md).
