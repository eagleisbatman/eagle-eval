"""The canonical Evaluation type for eagle-eval.

eagle-eval owns this type unconditionally and never substitutes a third
party's class for it. An earlier version imported ``langfuse.Evaluation``
when langfuse happened to be installed — but langfuse's Evaluation is
keyword-only (``Evaluation(*, name=, value=)``) while eagle-eval's own
evaluators construct it positionally (``Evaluation(name, value, comment)``).
That made the engine's behavior depend on whether an optional dependency was
present: graders worked with langfuse absent and crashed with it installed,
with no code change. Result destinations (e.g. langfuse upload) consume an
Evaluation only by attribute (``.name``/``.value``/``.comment``), so reusing
langfuse's class was never required. Keep this class self-owned.
"""

from __future__ import annotations


class Evaluation:
    """A single named score with an optional value and free-text comment.

    ``value=None`` is a deliberate "not applicable to this item" signal that
    callers exclude from aggregation; it is not an error.
    """

    __slots__ = ("name", "value", "comment")

    def __init__(self, name: str, value: float | None = None, comment: str = "") -> None:
        self.name = name
        self.value = value
        self.comment = comment

    def __repr__(self) -> str:
        return f"Evaluation(name={self.name!r}, value={self.value!r}, comment={self.comment!r})"
