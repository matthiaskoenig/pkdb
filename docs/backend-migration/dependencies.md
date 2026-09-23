---
search:
  exclude: true
---

# Dependency compatibility evidence

Resolved from stable packages into `backend-next/uv.lock`.

| Package | Locked version |
| --- | --- |
| pydantic | 2.13.5 |
| pydantic-core | 2.46.5 |
| pydantic-settings | 2.15.0 |
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| pandas | 2.3.3 |
| pint | 0.26.1 |
| openpyxl | 3.1.5 |
| pkdb-analysis | 0.2.2 |
| pytest | 9.1.1 |
| ruff | 0.16.8 |
| ty | 0.0.82 |

Verified locally on CPython 3.13.1 and 3.14.6 (standard GIL builds):

- Locked installation succeeded in independent environments.
- Runtime/configuration tests: 3 passed on each interpreter.
- Ruff and ty passed; ty uses Python 3.13 language semantics.
- Built sdist and wheel; installed wheel in clean environments on both interpreters.
- Clean-wheel imports include NumPy, SciPy, pandas, Pint, and the PK calculation module.

The unchanged pkdb-analysis import prints legacy environment-configuration warnings; it did not make a network request. Domain integration must not use its API client or import default remote configuration as an application fallback.

Runtime scientific regression, PostgreSQL, REST/MCP, and container gates remain pending; packaging success does not establish scientific or API compatibility.
