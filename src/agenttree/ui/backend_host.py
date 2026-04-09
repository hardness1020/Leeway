"""JSON-lines backend host for the React terminal frontend."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from agenttree.api.client import SupportsStreamingMessages
from agenttree.engine.stream_events import (
    AssistantTextDelta,
    AssistantTurnComplete,
    StreamEvent,
    ToolExecutionCompleted,
    ToolExecutionStarted,
)
from agenttree.ui.protocol import BackendEvent, FrontendRequest, TranscriptItem
from agenttree.ui.runtime import build_runtime, close_runtime, get_command_names, handle_line, start_runtime

_PROTOCOL_PREFIX = "ATJSON:"


@dataclass(frozen=True)
class BackendHostConfig:
    """Configuration for one backend host session."""

    model: str | None = None
    base_url: str | None = None
    system_prompt: str | None = None
    api_key: str | None = None
    api_format: str | None = None
    api_client: SupportsStreamingMessages | None = None


class ReactBackendHost:
    """Drive the AgentTree runtime over a structured stdin/stdout protocol."""

    def __init__(self, config: BackendHostConfig) -> None:
        self._config = config
        self._bundle = None
        self._write_lock = asyncio.Lock()
        self._request_queue: asyncio.Queue[FrontendRequest] = asyncio.Queue()
        self._permission_requests: dict[str, asyncio.Future[bool]] = {}
        self._question_requests: dict[str, asyncio.Future[str]] = {}
        self._busy = False
        self._running = True
        self._current_task: asyncio.Task | None = None
        self._unsubscribe_state: Callable[[], None] | None = None

    async def run(self) -> int:
        self._bundle = await build_runtime(
            model=self._config.model,
            base_url=self._config.base_url,
            system_prompt=self._config.system_prompt,
            api_key=self._config.api_key,
            api_format=self._config.api_format,
            api_client=self._config.api_client,
            permission_prompt=self._ask_permission,
            ask_user_prompt=self._ask_question,
        )
        await start_runtime(self._bundle)

        # Push state changes to frontend in real-time (e.g. during workflow execution)
        def _on_state_change(new_state) -> None:
            asyncio.ensure_future(self._emit(BackendEvent.status_snapshot(state=new_state)))

        self._unsubscribe_state = self._bundle.app_state.subscribe(_on_state_change)

        await self._emit(BackendEvent.ready(self._bundle.app_state.get(), commands=get_command_names(self._bundle.cwd)))
        await self._emit(BackendEvent.status_snapshot(state=self._bundle.app_state.get()))

        reader = asyncio.create_task(self._read_requests())
        try:
            while self._running:
                request = await self._request_queue.get()
                if request.type == "shutdown":
                    if self._current_task and not self._current_task.done():
                        self._current_task.cancel()
                    await self._emit(BackendEvent(type="shutdown"))
                    break
                if request.type == "cancel":
                    if self._current_task and not self._current_task.done():
                        self._current_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await self._current_task
                        self._current_task = None
                        self._busy = False
                        await self._emit(
                            BackendEvent(
                                type="transcript_item",
                                item=TranscriptItem(role="system", text="Generation cancelled."),
                            )
                        )
                        await self._emit(BackendEvent(type="line_complete"))
                    continue
                if request.type == "permission_response":
                    if request.request_id in self._permission_requests:
                        self._permission_requests[request.request_id].set_result(bool(request.allowed))
                    continue
                if request.type == "question_response":
                    if request.request_id in self._question_requests:
                        self._question_requests[request.request_id].set_result(request.answer or "")
                    continue
                if request.type != "submit_line":
                    await self._emit(BackendEvent(type="error", message=f"Unknown request type: {request.type}"))
                    continue
                if self._busy:
                    await self._emit(BackendEvent(type="error", message="Session is busy"))
                    continue
                line = (request.line or "").strip()
                if not line:
                    continue
                self._busy = True
                self._current_task = asyncio.create_task(self._run_line(line))
        finally:
            if self._unsubscribe_state is not None:
                self._unsubscribe_state()
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._current_task
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader
            if self._bundle is not None:
                await close_runtime(self._bundle)
        return 0

    async def _run_line(self, line: str) -> None:
        """Run _process_line as a cancellable task."""
        try:
            should_continue = await self._process_line(line)
            if not should_continue:
                await self._emit(BackendEvent(type="shutdown"))
                self._running = False
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._emit(BackendEvent(type="error", message=str(exc)))
        finally:
            self._busy = False
            self._current_task = None

    async def _read_requests(self) -> None:
        while True:
            raw = await asyncio.to_thread(sys.stdin.buffer.readline)
            if not raw:
                await self._request_queue.put(FrontendRequest(type="shutdown"))
                return
            payload = raw.decode("utf-8").strip()
            if not payload:
                continue
            try:
                request = FrontendRequest.model_validate_json(payload)
            except Exception as exc:
                await self._emit(BackendEvent(type="error", message=f"Invalid request: {exc}"))
                continue
            await self._request_queue.put(request)

    async def _process_line(self, line: str) -> bool:
        assert self._bundle is not None
        await self._emit(
            BackendEvent(type="transcript_item", item=TranscriptItem(role="user", text=line))
        )

        async def _print_system(message: str) -> None:
            await self._emit(
                BackendEvent(type="transcript_item", item=TranscriptItem(role="system", text=message))
            )

        async def _render_event(event: StreamEvent) -> None:
            if isinstance(event, AssistantTextDelta):
                await self._emit(BackendEvent(type="assistant_delta", message=event.text))
                return
            if isinstance(event, AssistantTurnComplete):
                await self._emit(
                    BackendEvent(
                        type="assistant_complete",
                        message=event.message.text.strip(),
                        item=TranscriptItem(role="assistant", text=event.message.text.strip()),
                    )
                )
                return
            if isinstance(event, ToolExecutionStarted):
                await self._emit(
                    BackendEvent(
                        type="tool_started",
                        tool_name=event.tool_name,
                        tool_input=event.tool_input,
                        item=TranscriptItem(
                            role="tool",
                            text=f"{event.tool_name} {json.dumps(event.tool_input, ensure_ascii=True)}",
                            tool_name=event.tool_name,
                            tool_input=event.tool_input,
                        ),
                    )
                )
                return
            if isinstance(event, ToolExecutionCompleted):
                await self._emit(
                    BackendEvent(
                        type="tool_completed",
                        tool_name=event.tool_name,
                        output=event.output,
                        is_error=event.is_error,
                        item=TranscriptItem(
                            role="tool_result",
                            text=event.output,
                            tool_name=event.tool_name,
                            is_error=event.is_error,
                        ),
                    )
                )
                await self._emit(BackendEvent.status_snapshot(state=self._bundle.app_state.get()))

        async def _clear_output() -> None:
            await self._emit(BackendEvent(type="clear_transcript"))

        async def _select_request(title: str, submit_prefix: str, options: list) -> None:
            await self._emit(
                BackendEvent(
                    type="select_request",
                    modal={"kind": "select", "title": title, "submit_prefix": submit_prefix},
                    select_options=options,
                )
            )

        should_continue = await handle_line(
            self._bundle,
            line,
            print_system=_print_system,
            render_event=_render_event,
            clear_output=_clear_output,
            select_request=_select_request,
        )
        await self._emit(BackendEvent.status_snapshot(state=self._bundle.app_state.get()))
        await self._emit(BackendEvent(type="line_complete"))
        return should_continue

    async def _ask_permission(self, tool_name: str, reason: str) -> bool:
        request_id = uuid4().hex
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._permission_requests[request_id] = future
        await self._emit(
            BackendEvent(
                type="modal_request",
                modal={
                    "kind": "permission",
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "reason": reason,
                },
            )
        )
        try:
            return await future
        finally:
            self._permission_requests.pop(request_id, None)

    async def _ask_question(self, question: str) -> str:
        request_id = uuid4().hex
        future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        self._question_requests[request_id] = future
        await self._emit(
            BackendEvent(
                type="modal_request",
                modal={
                    "kind": "question",
                    "request_id": request_id,
                    "question": question,
                },
            )
        )
        try:
            return await future
        finally:
            self._question_requests.pop(request_id, None)

    async def _emit(self, event: BackendEvent) -> None:
        async with self._write_lock:
            sys.stdout.write(_PROTOCOL_PREFIX + event.model_dump_json() + "\n")
            sys.stdout.flush()


async def run_backend_host(
    *,
    model: str | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
    cwd: str | None = None,
    api_client: SupportsStreamingMessages | None = None,
) -> int:
    """Run the structured React backend host."""
    if cwd:
        os.chdir(cwd)
    host = ReactBackendHost(
        BackendHostConfig(
            model=model,
            base_url=base_url,
            system_prompt=system_prompt,
            api_key=api_key,
            api_format=api_format,
            api_client=api_client,
        )
    )
    return await host.run()


__all__ = ["run_backend_host", "ReactBackendHost", "BackendHostConfig"]
