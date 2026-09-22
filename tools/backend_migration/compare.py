"""Compare JSON contracts without concealing meaningful differences."""

from collections.abc import Mapping


def compare_records(
    expected: object, actual: object, *, ignored_paths: frozenset[str]
) -> list[str]:
    """Return deterministic differing paths; exclusions are exact, never recursive."""
    differences: list[str] = []

    def visit(left: object, right: object, path: str) -> None:
        """Visit."""
        if path in ignored_paths:
            return
        if type(left) is not type(right):
            differences.append(path)
        elif isinstance(left, Mapping) and isinstance(right, Mapping):
            for key in sorted(left.keys() | right.keys()):
                child = f"{path}.{key}"
                if child in ignored_paths:
                    continue
                if key not in left or key not in right:
                    differences.append(child)
                else:
                    visit(left[key], right[key], child)
        elif isinstance(left, list) and isinstance(right, list):
            for index in range(max(len(left), len(right))):
                child = f"{path}[{index}]"
                if child in ignored_paths:
                    continue
                if index >= len(left) or index >= len(right):
                    differences.append(child)
                else:
                    visit(left[index], right[index], child)
        elif left != right:
            differences.append(path)

    visit(expected, actual, "$")
    return differences
