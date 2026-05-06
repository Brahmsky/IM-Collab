import type { TaskListResponse, TaskDetailResponse, AppendResponse, ActionResponse, ErrorResponse, SSEPayload } from '@/types/task'

const API_BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await response.json()
  if (!response.ok || (data as ErrorResponse).ok === false) {
    throw new Error((data as ErrorResponse).error || 'Request failed')
  }
  return data as T
}

export function fetchTasks(): Promise<TaskListResponse> {
  return request<TaskListResponse>(`${API_BASE}/tasks`)
}

export function fetchTaskDetail(taskId: string): Promise<TaskDetailResponse> {
  return request<TaskDetailResponse>(`${API_BASE}/tasks/${encodeURIComponent(taskId)}`)
}

export function appendInstruction(taskId: string, text: string): Promise<AppendResponse> {
  return request<AppendResponse>(`${API_BASE}/tasks/${encodeURIComponent(taskId)}/append`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export function interruptTask(taskId: string): Promise<ActionResponse> {
  return request<ActionResponse>(`${API_BASE}/tasks/${encodeURIComponent(taskId)}/interrupt`, {
    method: 'POST',
    body: '{}',
  })
}

export function ackTask(taskId: string, note?: string): Promise<ActionResponse> {
  return request<ActionResponse>(`${API_BASE}/tasks/${encodeURIComponent(taskId)}/ack`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  })
}

export function retryTask(taskId: string, publish?: boolean): Promise<ActionResponse> {
  return request<ActionResponse>(`${API_BASE}/tasks/${encodeURIComponent(taskId)}/retry`, {
    method: 'POST',
    body: JSON.stringify({ publish: publish ?? false }),
  })
}

export function renameSession(sessionKey: string, sessionTitle: string): Promise<ActionResponse> {
  return request<ActionResponse>(`${API_BASE}/sessions/${encodeURIComponent(sessionKey)}/rename`, {
    method: 'POST',
    body: JSON.stringify({ session_title: sessionTitle }),
  })
}

export function deleteSession(sessionKey: string): Promise<ActionResponse> {
  return request<ActionResponse>(`${API_BASE}/sessions/${encodeURIComponent(sessionKey)}`, {
    method: 'DELETE',
  })
}

export interface SSECallbacks {
  onEvent: (payload: SSEPayload) => void
  onDone?: () => void
  onError?: (error: Event) => void
}

export function connectTaskStream(taskId: string, callbacks: SSECallbacks): EventSource {
  const url = `${API_BASE}/tasks/${encodeURIComponent(taskId)}/stream`
  const es = new EventSource(url)
  es.onmessage = (event) => {
    const payload = JSON.parse(event.data) as SSEPayload
    callbacks.onEvent(payload)
    if (payload.done) {
      es.close()
      callbacks.onDone?.()
    }
  }
  es.onerror = (event) => {
    es.close()
    callbacks.onError?.(event)
  }
  return es
}
