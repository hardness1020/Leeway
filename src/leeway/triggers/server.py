"""Lightweight HTTP trigger server."""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from leeway.cron.types import ShellAction, WebhookAction, WorkflowAction
from leeway.tasks.manager import BackgroundTaskManager
from leeway.triggers.registry import TriggerRegistry

logger = logging.getLogger(__name__)


class TriggerServer:
    """Async HTTP server that listens for webhook triggers.

    Uses asyncio's low-level server (no external deps needed).
    """

    def __init__(
        self,
        registry: TriggerRegistry,
        task_manager: BackgroundTaskManager,
        host: str = "127.0.0.1",
        port: int = 7432,
    ) -> None:
        self._registry = registry
        self._task_manager = task_manager
        self._host = host
        self._port = port
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_connection, self._host, self._port
        )
        logger.info("Trigger server listening on %s:%d", self._host, self._port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = await reader.readline()
            parts = request_line.decode().strip().split()
            if len(parts) < 2:
                await self._send_response(writer, 400, {"error": "Bad request"})
                return

            method, path = parts[0], parts[1]

            # Read headers
            headers: dict[str, str] = {}
            while True:
                line = await reader.readline()
                decoded = line.decode().strip()
                if not decoded:
                    break
                if ":" in decoded:
                    key, val = decoded.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            # Read body (max 1MB to prevent DoS)
            MAX_BODY = 1_048_576
            try:
                content_length = int(headers.get("content-length", "0"))
            except ValueError:
                await self._send_response(writer, 400, {"error": "Invalid Content-Length"})
                return
            if content_length > MAX_BODY:
                await self._send_response(writer, 413, {"error": "Payload too large"})
                return
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)

            # Route
            if method == "GET" and path == "/health":
                await self._send_response(writer, 200, {"status": "ok"})
            elif method == "GET" and path == "/triggers":
                triggers = self._registry.list()
                data = [{"id": t.id, "name": t.name, "enabled": t.enabled} for t in triggers]
                await self._send_response(writer, 200, {"triggers": data})
            elif method == "POST" and path.startswith("/trigger/"):
                trigger_id = path.split("/trigger/", 1)[1].rstrip("/")
                secret = headers.get("x-trigger-secret", "")
                await self._handle_trigger(writer, trigger_id, secret, body)
            else:
                await self._send_response(writer, 404, {"error": "Not found"})

        except Exception:
            logger.exception("Error handling trigger request")
            try:
                await self._send_response(writer, 500, {"error": "Internal error"})
            except Exception:
                pass
        finally:
            writer.close()

    async def _handle_trigger(
        self,
        writer: asyncio.StreamWriter,
        trigger_id: str,
        secret: str,
        body: bytes,
    ) -> None:
        trigger = self._registry.get(trigger_id)
        if trigger is None:
            await self._send_response(writer, 404, {"error": "Trigger not found"})
            return

        if not trigger.enabled:
            await self._send_response(writer, 403, {"error": "Trigger disabled"})
            return

        if not hmac.compare_digest(secret, trigger.secret):
            await self._send_response(writer, 401, {"error": "Invalid secret"})
            return

        # Fire the action
        action = trigger.action
        try:
            if isinstance(action, ShellAction):
                task = await self._task_manager.create_shell_task(
                    command=action.command,
                    cwd=action.cwd,
                    description=f"trigger:{trigger.name}",
                )
            elif isinstance(action, WorkflowAction):
                task = await self._task_manager.create_workflow_task(
                    workflow_name=action.workflow_name,
                    context=action.context,
                    description=f"trigger:{trigger.name}",
                )
            elif isinstance(action, WebhookAction):
                import httpx

                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.request(method=action.method, url=action.url, json=action.body)
                task = None
            else:
                await self._send_response(writer, 400, {"error": "Unknown action type"})
                return
        except Exception as exc:
            await self._send_response(writer, 500, {"error": str(exc)})
            return

        trigger.last_triggered = datetime.now(timezone.utc)
        trigger.trigger_count += 1
        self._registry.save(trigger)

        result: dict[str, Any] = {"status": "fired", "trigger": trigger.name}
        if task is not None:
            result["task_id"] = task.id
        await self._send_response(writer, 200, result)

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        body: dict[str, Any],
    ) -> None:
        phrases = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 413: "Payload Too Large", 500: "Internal Server Error"}
        phrase = phrases.get(status, "Unknown")
        payload = json.dumps(body).encode()
        response = (
            f"HTTP/1.1 {status} {phrase}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"\r\n"
        ).encode() + payload
        writer.write(response)
        await writer.drain()
