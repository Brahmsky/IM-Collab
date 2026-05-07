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

export interface ArtifactRemote {
  provider: string;
  url?: string;
  web_url?: string;
  permalink?: string;
  document_id?: string;
  xml_presentation_id?: string;
  whiteboard_token?: string;
  token?: string;
  id?: string;
}

export interface ArtifactInput {
  format?: string;
  path?: string;
}

export interface ArtifactOutput extends ArtifactRemote {
  object_type?: string;
}

export interface ArtifactDisplay {
  card_kind?: DisplayArtifactKind;
  label?: string;
  click_url?: string;
  preview_value?: string;
  clickable?: boolean;
}

export interface ArtifactDelivery {
  feishu_card_mode?: 'link_button' | 'markdown_fallback' | 'file_preview';
}

export interface ArtifactItem {
  id: string;
  kind: string;
  family?: string;
  title?: string;
  path?: string;
  input?: ArtifactInput | null;
  output?: ArtifactOutput | null;
  display?: ArtifactDisplay | null;
  delivery?: ArtifactDelivery | null;
  remote?: ArtifactRemote;
  url?: string | null;
  clickable?: boolean;
  source_task_id?: string | null;
}

export interface Artifacts {
  task_id: string;
  summary: string;
  next_steps: string[];
  items: ArtifactItem[];
}

export type DisplayArtifactKind = 'document' | 'slides' | 'whiteboard' | 'sheet' | 'file';

export interface DisplayArtifact {
  id: string;
  title: string;
  kind: DisplayArtifactKind;
  url?: string;
  value?: string;
}

export interface TaskDetailResponse {
  task: TaskSummary;
  chat_messages: ChatMessage[];
  control_commands: ControlCommand[];
  artifacts: Artifacts;
  current_turn_artifacts: ArtifactItem[];
  session_artifacts: ArtifactItem[];
  pending_controls: boolean;
}

export interface AppendResponse {
  ok: true;
  task_id: string;
  stream_url: string;
  backend?: string;
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
  current_turn_artifacts: ArtifactItem[];
  error: string | null;
}
