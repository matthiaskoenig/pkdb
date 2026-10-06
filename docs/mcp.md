# MCP for agents

PK-DB provides a **read-only** Model Context Protocol (MCP) server at `/mcp/`. Agents can find and retrieve data authorized for their account. The server does not expose study validation, uploads, replacement, deletion, or account changes. Use the [Python client and REST API](api.md) for curation.

## Connect

Create a personal API key with the `read` scope in **Account settings → API keys**. Configure your MCP client for Streamable HTTP with:

- URL: `https://beta.pk-db.com/mcp/` (local development: `http://localhost:18083/mcp/`).
- Header: `Authorization: Bearer <your-personal-api-key>`.

Keep the key in the client's secret store or environment configuration. Do not include it in prompts or checked-in configuration. The server checks the current key on requests, including requests in an established session. Revoked keys stop working. Private study access follows the same permissions as the REST API.

## Tools

| Tool | Purpose | Arguments |
| --- | --- | --- |
| `search_studies` | Find authorized studies | `query`: study query with predicates and pagination |
| `get_study` | Retrieve a complete canonical study | `sid`: `<substance>/<name>`, a study format 1 identifier, or a PKDB identifier |
| `query_data` | Query measurements and related entities | `query`: data query with predicates and pagination |

All tools advertise `readOnlyHint: true` and `destructiveHint: false`. `validate_study` and `replace_study` are not available, even to administrators or API keys that also have write scopes.

### Find studies

Call `search_studies` with:

```json
{
  "query": {
    "entity": "studies",
    "page": 1,
    "page_size": 20
  }
}
```

This compatibility tool returns `items` and `count`. For the common data pagination format, use `query_data` with the same arguments instead.

### Read a study

Call `get_study` with:

```json
{"sid": "caffeine/Harder1988"}
```

`sid` is the identifier of a study in study format 2 (`<substance>/<name>`), the identifier of a study in study format 1 (such as `PKDB01110`), the PKDB identifier of a released study (such as `PKDB00198`), or the former study format 1 identifier of a study that a study format 2 upload took over (such as `Vilsboll2008`). The tool reads the study of a PKDB identifier or former identifier directly, without the redirect of the REST API. A PKDB identifier or former identifier names a private study only for its readers: anyone else gets `Not found`, like REST, so the identifier does not reveal that the study exists.

The result is the complete canonical study definition, including its reference, groups, individuals, interventions, measurements, and attachment metadata. Statistics have no `value` and interventions have structured schedules, as described under [statistics in responses](api.md#statistics-in-responses); `metadata` carries the release (`pkdb_id` and date), the curation issue number and the review status and items of a study in study format 2.

### Query measurements

Call `query_data` with:

```json
{
  "query": {
    "entity": "measurements",
    "page": 1,
    "page_size": 20
  }
}
```

The result uses `items`, `total`, `page`, `page_size`, `next`, and `previous`. `next` and `previous` are page numbers or `null`; pass `next` as `query.page` to continue. The tool shares the REST query service, including field validation, bounded pagination, and private-data filtering. See the [API guide](api.md) for predicate syntax and the distinction between study-wide and measurement filters.

## Moving curation clients to REST

Clients that previously called `validate_study` or `replace_study` receive an unknown-tool error. Replace those calls with authenticated REST validation and upload requests, or use `pkdb validate` and `pkdb upload` as described in the [local upload guide](local-upload-testing.md). No write-tool alias is retained.
