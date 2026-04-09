import React from 'react';
import {Box, Text} from 'ink';

import type {TaskSnapshot} from '../types.js';

const SEP = ' \u2502 ';
const DEFAULT_CONTEXT_WINDOW = 200_000;

export function StatusBar({status, tasks}: {status: Record<string, unknown>; tasks: TaskSnapshot[]}): React.JSX.Element {
	const model = String(status.model ?? 'unknown');
	const mode = String(status.permission_mode ?? 'default');
	const inputTokens = Number(status.input_tokens ?? 0);
	const outputTokens = Number(status.output_tokens ?? 0);
	const sessionStartMs = Number(status.session_start_ms ?? 0);
	const workflowName = String(status.workflow_name ?? '');
	const workflowNode = String(status.workflow_node ?? '');
	const workflowBranches = (status.workflow_parallel_branches ?? []) as string[];

	const hasTokens = inputTokens > 0 || outputTokens > 0;
	const contextPct = hasTokens
		? Math.min(100, Math.round(((inputTokens + outputTokens) / DEFAULT_CONTEXT_WINDOW) * 100))
		: 0;
	const hasDuration = sessionStartMs > 0;
	const hasWorkflow = workflowName.length > 0;

	return (
		<Box flexDirection="column">
			{/* Line 1 */}
			<Box flexDirection="row">
				<Text>
					<Text color="cyan">{'\u25C6 '}</Text>
					<Text bold>{model}</Text>
					{hasTokens ? (
						<>
							<Text dimColor>{SEP}</Text>
							<ContextBar percentage={contextPct} />
							<Text> </Text>
							<ContextPctText percentage={contextPct} />
							<Text dimColor>{SEP}</Text>
							<Text dimColor>{formatNum(inputTokens)}{'\u2193'} {formatNum(outputTokens)}{'\u2191'}</Text>
						</>
					) : null}
					{hasDuration ? (
						<>
							<Text dimColor>{SEP}</Text>
							<Text dimColor>{formatDuration(sessionStartMs)}</Text>
						</>
					) : null}
					<Text dimColor>{SEP}</Text>
					<Text dimColor>{mode}</Text>
				</Text>
			</Box>

			{/* Line 2 — workflow indicator (only when active) */}
			{hasWorkflow ? (
				<Box flexDirection="row">
					<Text>
						<Text color="green">{'\u25B6 '}</Text>
						<Text color="magenta">{workflowName}</Text>
						{workflowNode ? (
							<>
								<Text dimColor>{' @ '}</Text>
								<Text color="cyan">{workflowNode}</Text>
							</>
						) : null}
						{workflowBranches.length > 0 ? (
							<Text color="yellow">{' ['}{workflowBranches.join(', ')}{']'}</Text>
						) : null}
					</Text>
				</Box>
			) : null}
		</Box>
	);
}

function ContextBar({percentage}: {percentage: number}): React.JSX.Element {
	const width = 20;
	const filled = Math.round((percentage / 100) * width);
	const empty = width - filled;
	const color = percentage > 85 ? 'red' : percentage > 60 ? 'yellow' : 'green';

	return (
		<Text>
			<Text color={color}>{'\u2588'.repeat(filled)}</Text>
			<Text dimColor>{'\u2591'.repeat(empty)}</Text>
		</Text>
	);
}

function ContextPctText({percentage}: {percentage: number}): React.JSX.Element {
	const color = percentage > 85 ? 'red' : percentage > 60 ? 'yellow' : 'green';
	return <Text color={color}>{percentage}%</Text>;
}

function formatNum(n: number): string {
	if (n >= 1_000_000) {
		return `${(n / 1_000_000).toFixed(1)}M`;
	}
	if (n >= 1000) {
		return `${(n / 1000).toFixed(1)}k`;
	}
	return String(n);
}

function formatDuration(startMs: number): string {
	const elapsed = Math.floor((Date.now() - startMs) / 1000);
	if (elapsed < 0) return '';
	if (elapsed < 60) return `${elapsed}s`;
	const min = Math.floor(elapsed / 60);
	const sec = elapsed % 60;
	if (min < 60) return `${min}m ${sec}s`;
	const hr = Math.floor(min / 60);
	const rm = min % 60;
	return `${hr}h ${rm}m`;
}
