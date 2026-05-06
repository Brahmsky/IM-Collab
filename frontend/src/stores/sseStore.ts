import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { connectTaskStream } from '@/utils/api'
import { useTaskStore } from './taskStore'
import { useChatStore } from './chatStore'
import type { SSEPayload } from '@/types/task'

export type StreamState = 'idle' | 'connecting' | 'streaming' | 'done'

export const useSseStore = defineStore('sse', () => {
  const activeStream = ref<EventSource | null>(null)
  const streamState = ref<StreamState>('idle')
  const streamTexts = ref<string[]>([])
  const latestPayload = ref<SSEPayload | null>(null)

  const taskStore = useTaskStore()
  const chatStore = useChatStore()

  const isStreaming = computed(() => streamState.value === 'streaming')

  function connectStream(taskId: string) {
    if (activeStream.value) {
      disconnectStream()
    }
    
    streamState.value = 'connecting'
    streamTexts.value = []
    latestPayload.value = null

    const es = connectTaskStream(taskId, {
      onEvent: (payload) => {
        streamState.value = 'streaming'
        latestPayload.value = payload
        
        if (payload.stream_texts && payload.stream_texts.length > 0) {
          streamTexts.value = payload.stream_texts
        }

        if (taskStore.selectedTaskDetail) {
          taskStore.selectedTaskDetail.task.state = payload.state
          if (payload.artifacts) {
            taskStore.selectedTaskDetail.artifacts = payload.artifacts
          }
          taskStore.selectedTaskDetail.pending_controls = payload.pending_controls
        }
      },
      onDone: () => {
        streamState.value = 'done'
        if (streamTexts.value.length > 0) {
          chatStore.addAssistantMessage(streamTexts.value.join(''))
        }
        taskStore.fetchTaskDetail(taskId)
      },
      onError: (err) => {
        console.error('SSE Error:', err)
        streamState.value = 'done'
      }
    })

    activeStream.value = es
  }

  function disconnectStream() {
    if (activeStream.value) {
      activeStream.value.close()
      activeStream.value = null
    }
    streamState.value = 'idle'
  }

  function reset() {
    disconnectStream()
    streamTexts.value = []
    latestPayload.value = null
  }

  return {
    activeStream,
    streamState,
    streamTexts,
    latestPayload,
    isStreaming,
    connectStream,
    disconnectStream,
    reset
  }
})
