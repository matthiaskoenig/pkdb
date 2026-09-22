"""Validated relationship index for one vocabulary compilation."""

from collections.abc import Iterable, Iterator, Sequence
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from info_nodes.node import InfoNode


class NodeIndex(Sequence["InfoNode"]):
    """Index a completed graph; rebuild after editing nodes or their parents."""

    def __init__(self, nodes: Iterable[InfoNode]):
        self._nodes = tuple(nodes)
        self.by_sid = {node.sid: node for node in self._nodes}
        if len(self.by_sid) != len(self._nodes):
            raise ValueError("Duplicate vocabulary SID")
        children: dict[str, list[InfoNode]] = {sid: [] for sid in self.by_sid}
        for node in self._nodes:
            for parent in dict.fromkeys(node.parents):
                if parent not in children:
                    raise ValueError(f"Unknown parent {parent} for {node.sid}")
                children[parent].append(node)
        self.children = {sid: tuple(values) for sid, values in children.items()}
        self._choices: dict[str, tuple[str, ...]] = {}
        active: set[str] = set()
        done: set[str] = set()

        def visit(sid: str) -> None:
            if sid in active:
                raise ValueError(f"Vocabulary cycle at {sid}")
            if sid in done:
                return
            active.add(sid)
            for child in self.children[sid]:
                visit(child.sid)
            active.remove(sid)
            done.add(sid)

        for sid in self.by_sid:
            visit(sid)

    @overload
    def __getitem__(self, index: int) -> InfoNode: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[InfoNode, ...]: ...

    def __getitem__(self, index: int | slice) -> InfoNode | tuple[InfoNode, ...]:
        return self._nodes[index]

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self) -> Iterator[InfoNode]:
        return iter(self._nodes)

    def choices(self, sid: str) -> tuple[str, ...]:
        """Return unique choices in definition order, stopping at measurements."""
        if sid not in self._choices:
            choices = []
            for child in self.children[sid]:
                if not child.can_choice:
                    choices.extend(self.choices(child.sid))
                if child.ntype == "choice":
                    choices.append(child.sid)
            self._choices[sid] = tuple(dict.fromkeys(choices))
        return self._choices[sid]
