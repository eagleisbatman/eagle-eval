"""Evaluation object compatibility layer."""

try:
    from langfuse import Evaluation
except ImportError:
    class Evaluation:
        """Small fallback used when a result-destination SDK is not installed."""

        def __init__(self, name: str, value: float | None, comment: str = ""):
            self.name = name
            self.value = value
            self.comment = comment
