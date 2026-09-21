"""Inventory the actual legacy URL resolver without issuing write requests."""

import argparse
import json
from pathlib import Path


def collect_contracts() -> list[dict]:
    """Collect contracts."""
    import django

    django.setup()
    from django.urls import URLResolver, get_resolver

    contracts = {}

    def visit(patterns, prefix=""):
        """Visit."""
        for pattern in patterns:
            path = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                visit(pattern.url_patterns, path)
                continue
            callback = pattern.callback
            view = getattr(callback, "cls", getattr(callback, "view_class", None))
            actions = getattr(callback, "actions", {})
            if actions:
                methods = list(actions)
            elif view:
                methods = [
                    method
                    for method in getattr(view, "http_method_names", [])
                    if hasattr(view, method)
                ]
            else:
                methods = ["get"]
            serializer = getattr(view, "serializer_class", None)
            meta = getattr(serializer, "Meta", None)
            for method in methods:
                key = ("/" + path, method.upper())
                row = {
                    "path": key[0],
                    "method": key[1],
                    "view": f"{callback.__module__}.{callback.__name__}",
                    "action": actions.get(method),
                    "serializer": getattr(serializer, "__name__", None),
                    "fields": list(getattr(meta, "fields", [])),
                    "permissions": [
                        p.__name__ for p in getattr(view, "permission_classes", [])
                    ],
                    "characterization": "resolver_inventory",
                    "new_owner": "api/legacy_uploads.py"
                    if "/_" in key[0]
                    else "api/reads.py",
                }
                contracts.setdefault(key, row)

    visit(get_resolver().url_patterns)
    return [contracts[key] for key in sorted(contracts)]


def main():
    """Main."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps({"schema_version": 1, "routes": collect_contracts()}, indent=2)
        + "\n"
    )


if __name__ == "__main__":
    main()
