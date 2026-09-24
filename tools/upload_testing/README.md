# Isolated real-study upload verification

From the repository root, run:

```bash
bash tools/upload_testing/run.sh /path/to/pkdb_data/studies/apixaban /tmp/pkdb-upload-evidence
```

Docker is required. Each invocation creates a unique Compose project with a fresh PostgreSQL database and attachment directory in tmpfs. No ports are published. The study corpus and repository sources are mounted read-only. The exit trap removes only this invocation's containers and volumes.

The harness provisions an ephemeral administrator and scoped API key using the server's provisioning and credential services, imports the curator roster, and bootstraps missing study attribution accounts. Credentials stay inside the test process and are never written to evidence files.

It synchronizes the server vocabulary, runs the public `pkdb` CLI against all 30 studies, repeats uploads to verify replacement, and sends multipart bundles directly to the API to exercise server rejection independently of local validation. It checks saved studies through the API, matching counts/digests, absence of rejected studies, request IDs, and the unchanged source digest.

The evidence directory contains human-readable stdout, JSON Lines stdout, batch reports, individual backend reports, source/server revisions, vocabulary metadata and backend logs. Expected scientific failures produce CLI exit 1; the harness succeeds when mixed outcomes are internally consistent. The historical 24-valid/6-invalid split is recorded as a baseline, not forced by changing study data or validation rules. Evidence includes source data values, so choose an appropriate location when testing a private corpus.

Unit and API contract tests cover synthetic faults separately. This harness tests redirected human output and machine output; it does not itself emulate an interactive terminal or inject connection failures.
