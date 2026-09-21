## Summary

<!-- what does this change and why -->

## Checklist

- [ ] the pull request targets `develop`
- [ ] the tests pass against the services (`tox -e py3.9`) and the type check is clean (`tox -e ty`)
- [ ] `ruff check` and `ruff format` are clean, e.g., via `pre-commit run --all-files`
- [ ] public functions and classes have type annotations and a docstring
- [ ] user visible changes are in `release-notes/` and, if needed, in `docs/`
