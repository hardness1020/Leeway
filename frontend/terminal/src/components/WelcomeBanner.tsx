import React from 'react';
import {Box, Text} from 'ink';

const VERSION = '0.1.0';

// prettier-ignore
const LOGO = [
	'██╗     ███████╗███████╗██╗    ██╗ █████╗ ██╗   ██╗',
	'██║     ██╔════╝██╔════╝██║    ██║██╔══██╗╚██╗ ██╔╝',
	'██║     █████╗  █████╗  ██║ █╗ ██║███████║ ╚████╔╝ ',
	'██║     ██╔══╝  ██╔══╝  ██║███╗██║██╔══██║  ╚██╔╝  ',
	'███████╗███████╗███████╗╚███╔███╔╝██║  ██║   ██║   ',
	'╚══════╝╚══════╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝   ',
];

export function WelcomeBanner(): React.JSX.Element {
	return (
		<Box flexDirection="column" marginBottom={1}>
			<Box flexDirection="column" paddingX={0}>
				{LOGO.map((line, i) => (
					<Text key={i} color="cyan" bold>{line}</Text>
				))}
				<Text> </Text>
				<Text>
					<Text dimColor> A workflow-driven AI agent</Text>
					<Text dimColor>{'  '}v{VERSION}</Text>
				</Text>
				<Text> </Text>
				<Text>
					<Text dimColor> </Text>
					<Text color="cyan">Ctrl+C</Text>
					<Text dimColor> exit</Text>
				</Text>
			</Box>
		</Box>
	);
}
