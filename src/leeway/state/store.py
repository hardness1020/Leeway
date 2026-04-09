"""Observable application state store."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from leeway.state.app_state import AppState


Listener = Callable[[AppState], None]


class AppStateStore:
    """Very small observable state store."""

    def __init__(self, initial_state: AppState) -> None:
        self._state = initial_state
        self._listeners: list[Listener] = []

    def get(self) -> AppState:
        """Return the current state snapshot."""
        return self._state

    def set(self, **updates) -> AppState:
        """Update the state and notify listeners."""
        self._state = replace(self._state, **updates)
        for listener in list(self._listeners):
            listener(self._state)
        return self._state

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Register a listener and return an unsubscribe callback."""
        self._listeners.append(listener)

        def _unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _unsubscribe
