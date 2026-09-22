## Summary

<!-- what does this change and why -->

## Checklist

- [ ] the pull request targets `develop`
- [ ] the tests pass against PostgreSQL on Python 3.13 and 3.14 and `uv run --project backend ty check --project backend` is clean
- [ ] `ruff check` and `ruff format` are clean, e.g., via `pre-commit run --all-files`
- [ ] public functions and classes have type annotations and a docstring
- [ ] user visible changes are in `release-notes/` and, if needed, in `docs/`
