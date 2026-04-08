export type FrontendConfig = {
	backend_command: string[];
	initial_prompt?: string | null;
};

export type TranscriptItem = {
	role: 'system' | 'user' | 'assistant' | 'tool' | 'tool_result' | 'log';
	text: string;
	tool_name?: string;
	tool_input?: Record<string, unknown>;
	is_error?: boolean;
};

export type TaskSnapshot = {
	id: string;
	type: string;
	status: string;
	description: string;
	metadata: Record<string, string>;
};

export type McpServerSnapshot = {
	name: string;
	state: string;
	detail?: string;
	transport?: string;
	auth_configured?: boolean;
	tool_count?: number;
	resource_count?: number;
};

export type BridgeSessionSnapshot = {
	session_id: string;
	command: string;
	cwd: string;
	pid: number;
	status: string;
	started_at: number;
	output_path: string;
};

export type SelectOptionPayload = {
	value: string;
	label: string;
	description?: string;
};

export type BackendEvent = {
	type: string;
	message?: string | null;
	item?: TranscriptItem | null;
	state?: Record<string, unknown> | null;
	tasks?: TaskSnapshot[] | null;
	mcp_servers?: McpServerSnapshot[] | null;
	bridge_sessions?: BridgeSessionSnapshot[] | null;
	commands?: string[] | null;
	modal?: Record<string, unknown> | null;
	select_options?: SelectOptionPayload[] | null;
	tool_name?: string | null;
	output?: string | null;
	is_error?: boolean | null;
};
