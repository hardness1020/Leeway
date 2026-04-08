import React from 'react';
import {Box, Text} from 'ink';

import type {TranscriptItem} from '../types.js';
import {ToolCallDisplay} from './ToolCallDisplay.js';
import {WelcomeBanner} from './WelcomeBanner.js';

export function ConversationView({
	items,
	assistantBuffer,
	showWelcome,
}: {
	items: TranscriptItem[];
	assistantBuffer: string;
	showWelcome: boolean;
}): React.JSX.Element {
	// Show the most recent items that fit the viewport
	const visible = items.slice(-40);

	return (
		<Box flexDirection="column" flexGrow={1}>
			{showWelcome && items.length === 0 ? <WelcomeBanner /> : null}

			{visible.map((item, index) => (
				<MessageRow key={index} item={item} />
			))}

			{assistantBuffer ? (
				<Box flexDirection="row" marginTop={0}>
					<Text color="green" bold>{'\u23FA '}</Text>
					<Text>{assistantBuffer}</Text>
				</Box>
			) : null}
		</Box>
	);
}

function MessageRow({item}: {item: TranscriptItem}): React.JSX.Element {
	switch (item.role) {
		case 'user':
			return (
				<Box marginTop={1} marginBottom={0}>
					<Text>
						<Text color="white" bold>{'> '}</Text>
						<Text>{item.text}</Text>
					</Text>
				</Box>
			);

		case 'assistant':
			return (
				<Box marginTop={1} marginBottom={0} flexDirection="column">
					<Text>
						<Text color="green" bold>{'\u23FA '}</Text>
						<Text>{item.text}</Text>
					</Text>
				</Box>
			);

		case 'tool':
		case 'tool_result':
			return <ToolCallDisplay item={item} />;

		case 'system':
			return (
				<Box marginTop={0}>
					<Text>
						<Text color="yellow">{'\u2139 '}</Text>
						<Text color="yellow">{item.text}</Text>
					</Text>
				</Box>
			);

		case 'log':
			return (
				<Box>
					<Text dimColor>{item.text}</Text>
				</Box>
			);

		default:
			return (
				<Box>
					<Text>{item.text}</Text>
				</Box>
			);
	}
}
