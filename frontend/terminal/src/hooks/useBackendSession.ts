import {useEffect, useMemo, useRef, useState} from 'react';
import {spawn, type ChildProcessWithoutNullStreams} from 'node:child_process';
import readline from 'node:readline';

import type {
	BackendEvent,
	BridgeSessionSnapshot,
	FrontendConfig,
	McpServerSnapshot,
	SelectOptionPayload,
	TaskSnapshot,
	TranscriptItem,
} from '../types.js';

const PROTOCOL_PREFIX = 'ATJSON:';

export function useBackendSession(config: FrontendConfig, onExit: (code?: number | null) => void) {
	const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
	const [assistantBuffer, setAssistantBuffer] = useState('');
	const [status, setStatus] = useState<Record<string, unknown>>({});
	const [tasks, setTasks] = useState<TaskSnapshot[]>([]);
	const [commands, setCommands] = useState<string[]>([]);
	const [mcpServers, setMcpServers] = useState<McpServerSnapshot[]>([]);
	const [bridgeSessions, setBridgeSessions] = useState<BridgeSessionSnapshot[]>([]);
	const [modal, setModal] = useState<Record<string, unknown> | null>(null);
	const [selectRequest, setSelectRequest] = useState<{title: string; submitPrefix: string; options: SelectOptionPayload[]} | null>(null);
	const [busy, setBusy] = useState(false);
	const childRef = useRef<ChildProcessWithoutNullStreams | null>(null);
	const sentInitialPrompt = useRef(false);

	const sendRequest = (payload: Record<string, unknown>): void => {
		const child = childRef.current;
		if (!child || child.stdin.destroyed) {
			return;
		}
		child.stdin.write(JSON.stringify(payload) + '\n');
	};

	useEffect(() => {
		const [command, ...args] = config.backend_command;
		const child = spawn(command, args, {
			stdio: ['pipe', 'pipe', 'inherit'],
			env: process.env,
		});
		childRef.current = child;

		const reader = readline.createInterface({input: child.stdout});
		reader.on('line', (line) => {
			if (!line.startsWith(PROTOCOL_PREFIX)) {
				setTranscript((items) => [...items, {role: 'log', text: line}]);
				return;
			}
			const event = JSON.parse(line.slice(PROTOCOL_PREFIX.length)) as BackendEvent;
			handleEvent(event);
		});

		child.on('exit', (code) => {
			setTranscript((items) => [...items, {role: 'system', text: `backend exited with code ${code ?? 0}`}]);
			process.exitCode = code ?? 0;
			onExit(code);
		});

		return () => {
			reader.close();
			if (!child.killed) {
				child.kill();
			}
		};
	}, []);

	const handleEvent = (event: BackendEvent): void => {
		if (event.type === 'ready') {
			setStatus(event.state ?? {});
			setTasks(event.tasks ?? []);
			setCommands(event.commands ?? []);
			setMcpServers(event.mcp_servers ?? []);
			setBridgeSessions(event.bridge_sessions ?? []);
			if (config.initial_prompt && !sentInitialPrompt.current) {
				sentInitialPrompt.current = true;
				sendRequest({type: 'submit_line', line: config.initial_prompt});
				setBusy(true);
			}
			return;
		}
		if (event.type === 'state_snapshot') {
			setStatus(event.state ?? {});
			setMcpServers(event.mcp_servers ?? []);
			setBridgeSessions(event.bridge_sessions ?? []);
			return;
		}
		if (event.type === 'tasks_snapshot') {
			setTasks(event.tasks ?? []);
			return;
		}
		if (event.type === 'transcript_item' && event.item) {
			setTranscript((items) => [...items, event.item as TranscriptItem]);
			return;
		}
		if (event.type === 'assistant_delta') {
			setAssistantBuffer((value) => value + (event.message ?? ''));
			return;
		}
		if (event.type === 'assistant_complete') {
			const text = event.message ?? assistantBuffer;
			setTranscript((items) => [...items, {role: 'assistant', text}]);
			setAssistantBuffer('');
			setBusy(false);
			return;
		}
		if (event.type === 'line_complete') {
			setBusy(false);
			return;
		}
		if ((event.type === 'tool_started' || event.type === 'tool_completed') && event.item) {
			const enrichedItem: TranscriptItem = {
				...event.item,
				tool_name: event.item.tool_name ?? event.tool_name ?? undefined,
				tool_input: event.item.tool_input ?? undefined,
				is_error: event.item.is_error ?? event.is_error ?? undefined,
			};
			setTranscript((items) => [...items, enrichedItem]);
			return;
		}
		if (event.type === 'clear_transcript') {
			setTranscript([]);
			setAssistantBuffer('');
			return;
		}
		if (event.type === 'select_request') {
			const m = event.modal ?? {};
			setSelectRequest({
				title: String(m.title ?? 'Select'),
				submitPrefix: String(m.submit_prefix ?? ''),
				options: event.select_options ?? [],
			});
			return;
		}
		if (event.type === 'modal_request') {
			setModal(event.modal ?? null);
			return;
		}
		if (event.type === 'error') {
			setTranscript((items) => [...items, {role: 'system', text: `error: ${event.message ?? 'unknown error'}`}]);
			setBusy(false);
			return;
		}
		if (event.type === 'shutdown') {
			onExit(0);
		}
	};

	return useMemo(
		() => ({
			transcript,
			assistantBuffer,
			status,
			tasks,
			commands,
			mcpServers,
			bridgeSessions,
			modal,
			selectRequest,
			busy,
			setModal,
			setSelectRequest,
			setBusy,
			sendRequest,
		}),
		[assistantBuffer, bridgeSessions, busy, commands, mcpServers, modal, selectRequest, status, tasks, transcript]
	);
}
