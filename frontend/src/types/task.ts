export type TaskState = 'queued' | 'running' | 'waiting_for_user' | 'completed' | 'failed';

export interface TaskSummary {
  task_id: string;
  state: TaskState;
  created_at: string;
  updated_at: string;
  summary: string;
  session_key: string;
  session_title: string;
  chat_name: string;
  chat_id: string;
  codex_thread_id: string;
  artifact_outputs: [string, string][];
}

export interface TaskListResponse {
  tasks: TaskSummary[];
  events: {
    total: number;
    latest_files: string[];
  };
}

export interface ChatMessage {
  timestamp: string;
  role: 'user' | 'assistant';
  text: string;
  source: string;
}

export interface ControlCommand {
  timestamp: string;
  type: 'append_instruction' | 'interrupt' | 'confirm_instruction' | 'card_action';
  operator?: string;
  payload: Record<string, unknown>;
}

export interface ArtifactItem {
  id: string;
  kind: string;
  title?: string;
  path?: string;
  remote?: {
    provider: string;
    url?: string;
    document_id?: string;
    xml_presentation_id?: string;
    whiteboard_token?: string;
  };
}

export interface Artifacts {
  task_id: string;
  summary: string;
  next_steps: string[];
  items: ArtifactItem[];
}

export interface TaskDetailResponse {
  task: TaskSummary;
  chat_messages: ChatMessage[];
  control_commands: ControlCommand[];
  artifacts: Artifacts;
  pending_controls: boolean;
}

export interface AppendResponse {
  ok: true;
  task_id: string;
  stream_url: string;
}

export interface ActionResponse {
  ok: true;
  task_id?: string;
  generator?: string;
}

export interface ErrorResponse {
  ok: false;
  error: string;
}

export interface SSEPayload {
  ok: boolean;
  done: boolean;
  state: TaskState;
  pending_controls: boolean;
  stream_texts: string[];
  artifacts: Artifacts | null;
  error: string | null;
}
