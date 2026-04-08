import React from 'react';
import {Box, Text} from 'ink';

export type SelectOption = {
	value: string;
	label: string;
	description?: string;
	active?: boolean;
};

export function SelectModal({
	title,
	options,
	selectedIndex,
}: {
	title: string;
	options: SelectOption[];
	selectedIndex: number;
}): React.JSX.Element {
	return (
		<Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1} marginTop={1}>
			<Text bold color="cyan">{title}</Text>
			<Text> </Text>
			{options.map((opt, i) => {
				const isSelected = i === selectedIndex;
				const isCurrent = opt.active;
				return (
					<Box key={opt.value} flexDirection="row">
						<Text color={isSelected ? 'cyan' : undefined} bold={isSelected}>
							{isSelected ? '\u276F ' : '  '}
							<Text color={isSelected ? 'cyan' : undefined}>
								{opt.label}
							</Text>
						</Text>
						{isCurrent ? <Text color="green"> (current)</Text> : null}
						{opt.description ? <Text dimColor>  {opt.description}</Text> : null}
					</Box>
				);
			})}
			<Text> </Text>
			<Text dimColor>{'\u2191\u2193'} navigate{'  '}{'\u23CE'} select{'  '}esc cancel</Text>
		</Box>
	);
}
