# REST API

Use `https://alpha.pk-db.com` as the base URL for data access and curation. The [Python client](python-client.md) wraps common operations; you can also make HTTP requests directly. Consult the [interactive API reference](https://alpha.pk-db.com/docs) for endpoint schemas and available parameters.

## Browse studies and measurements

Public browsing does not require an API key:

```bash
curl --fail --get 'https://alpha.pk-db.com/api/v1/studies/' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=20'

curl --fail --get 'https://alpha.pk-db.com/api/v1/outputs/' \
  --data-urlencode 'study_sid=STUDY_SID' \
  --data-urlencode 'page=1' --data-urlencode 'page_size=20'
```

Replace `STUDY_SID` with a study identifier returned by the study list. Measurements use the `outputs` endpoint. The list response contains rows in `data.data`, a total in `data.count`, and pagination fields including `current_page` and `last_page`. Request subsequent pages to retrieve the complete selection.

| Endpoint | Use |
| --- | --- |
| `/api/v1/studies/` | Study summaries |
| `/api/v1/groups/` | Study groups and their characteristics |
| `/api/v1/individuals/` | Individual subjects |
| `/api/v1/interventions/` | Doses and other interventions |
| `/api/v1/outputs/` | Measurements |
| `/api/v1/references/` | Publications |
| `/api/v2/studies/{sid}` | Complete canonical study |
| `/api/v2/vocabulary` | Vocabulary snapshot for validation |

Study-level selections can include broader context than a measurement-level match. See [search scopes](web-interface.md#choose-the-scope-of-your-search) and the API reference before combining filters.

## Authenticate requests

Create a personal key in [Account settings](https://alpha.pk-db.com/account), then provide it through `PKDB_API_KEY` in your environment. Send it as a Bearer credential:

```bash
curl --fail --header "Authorization: Bearer ${PKDB_API_KEY}" \
  'https://alpha.pk-db.com/api/v1/studies/'
```

Authentication adds access only to studies your account is allowed to read. For key scopes, expiry, and rotation, see [Accounts and API keys](authentication.md).

## Download a dataset

Downloads require authentication, including downloads of public data:

```bash
curl --fail --get 'https://alpha.pk-db.com/api/v1/filter/' \
  --header "Authorization: Bearer ${PKDB_API_KEY}" \
  --data-urlencode 'studies__sid=STUDY_SID' \
  --data-urlencode 'download=true' \
  --output dataset.zip
```

The response is a ZIP archive restricted to data your account can access. Preserve the study identifiers, selection criteria, and retrieval date with your analysis. Follow the licences attached to the studies.

## Curate data

Use the [Python client preparation and upload workflow](python-client.md#prepare-validate-and-upload-a-study-folder) to send study folders to `https://alpha.pk-db.com`. It prepares and validates the source bundle and checks vocabulary compatibility before upload. A curator account and a key with `studies:write` are required; existing studies can be replaced only when your account has permission.

## Handle errors

Inspect the HTTP status and response body. Validation failures include structured issues where available. `401` indicates an authentication problem; `403` indicates insufficient access; `409` can indicate incompatible vocabulary or processing versions. On `429`, respect `Retry-After`. Do not automatically retry an upload with an uncertain outcome: inspect the study first.
