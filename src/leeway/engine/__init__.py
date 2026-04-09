"""Engine module - core agent loop."""


def __getattr__(name: str):
    if name == "QueryEngine":
        from leeway.engine.query_engine import QueryEngine
        return QueryEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["QueryEngine"]
