import React from 'react';
import {Box, Text} from 'ink';
import TextInput from 'ink-text-input';

export function ModalHost({
	modal,
	modalInput,
	setModalInput,
	onSubmit,
}: {
	modal: Record<string, unknown> | null;
	modalInput: string;
	setModalInput: (value: string) => void;
	onSubmit: (value: string) => void;
}): React.JSX.Element | null {
	if (modal?.kind === 'permission') {
		return (
			<Box flexDirection="column" marginTop={1}>
				<Text>
					<Text color="yellow" bold>{'\u250C '}</Text>
					<Text bold>Allow </Text>
					<Text color="cyan" bold>{String(modal.tool_name ?? 'tool')}</Text>
					<Text bold>?</Text>
				</Text>
				{modal.reason ? (
					<Text>
						<Text color="yellow">{'\u2502 '}</Text>
						<Text dimColor>{String(modal.reason)}</Text>
					</Text>
				) : null}
				<Text>
					<Text color="yellow">{'\u2514 '}</Text>
					<Text color="green">[y] Allow</Text>
					<Text>{'  '}</Text>
					<Text color="red">[n] Deny</Text>
				</Text>
			</Box>
		);
	}
	if (modal?.kind === 'question') {
		return (
			<Box flexDirection="column" marginTop={1}>
				<Text>
					<Text color="magenta" bold>{'\u2753 '}</Text>
					<Text bold>{String(modal.question ?? 'Question')}</Text>
				</Text>
				<Box>
					<Text color="cyan">{'> '}</Text>
					<TextInput value={modalInput} onChange={setModalInput} onSubmit={onSubmit} />
				</Box>
			</Box>
		);
	}
	if (modal?.kind === 'mcp_auth') {
		return (
			<Box flexDirection="column" marginTop={1}>
				<Text>
					<Text color="yellow" bold>{'\u{1F511} '}</Text>
					<Text bold>MCP Authentication</Text>
				</Text>
				<Text dimColor>{String(modal.prompt ?? 'Provide auth details')}</Text>
				<Box>
					<Text color="cyan">{'> '}</Text>
					<TextInput value={modalInput} onChange={setModalInput} onSubmit={onSubmit} />
				</Box>
			</Box>
		);
	}
	return null;
}
