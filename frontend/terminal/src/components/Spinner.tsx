import React, {useEffect, useState} from 'react';
import {Text} from 'ink';

const FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
const VERBS = [
	'Thinking',
	'Processing',
	'Analyzing',
	'Reasoning',
	'Working',
	'Computing',
	'Evaluating',
	'Considering',
];

export function Spinner({label}: {label?: string}): React.JSX.Element {
	const [frame, setFrame] = useState(0);
	const [verbIndex, setVerbIndex] = useState(0);

	useEffect(() => {
		const timer = setInterval(() => {
			setFrame((f) => (f + 1) % FRAMES.length);
		}, 80);
		return () => clearInterval(timer);
	}, []);

	useEffect(() => {
		const timer = setInterval(() => {
			setVerbIndex((v) => (v + 1) % VERBS.length);
		}, 3000);
		return () => clearInterval(timer);
	}, []);

	const verb = label ?? `${VERBS[verbIndex]}...`;

	return (
		<Text>
			<Text color="cyan">{FRAMES[frame]}</Text>
			<Text dimColor> {verb}</Text>
		</Text>
	);
}
