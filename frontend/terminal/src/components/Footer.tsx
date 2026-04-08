import React from 'react';
import {Box, Text} from 'ink';

export function Footer({status, taskCount}: {status: Record<string, unknown>; taskCount: number}): React.JSX.Element {
	return (
		<Box marginTop={1}>
			<Text dimColor>
				model={String(status.model ?? 'unknown')} provider={String(status.provider ?? 'unknown')} auth=
				{String(status.auth_status ?? 'unknown')} permission={String(status.permission_mode ?? 'unknown')} tasks=
				{String(taskCount)} mcp={String(status.mcp_connected ?? 0)}/{String(status.mcp_failed ?? 0)} bridge=
				{String(status.bridge_sessions ?? 0)} vim={String(Boolean(status.vim_enabled))} voice=
				{String(Boolean(status.voice_enabled))} effort={String(status.effort ?? 'medium')} passes=
				{String(status.passes ?? 1)}
			</Text>
		</Box>
	);
}
