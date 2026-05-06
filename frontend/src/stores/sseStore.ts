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
    disconnectStream()
    streamState.value = 'connecting'
    streamTexts.value = []
    latestPayload.value = null

    const es = connectTaskStream(taskId, {
      onEvent: (payload) => {
        if (streamState.value !== 'done') {
          streamState.value = 'streaming'
        }
        latestPayload.value = payload
        if (payload.stream_texts?.length) {
          streamTexts.value = [...payload.stream_texts]
        }
      },
      onDone: () => {
        streamState.value = 'done'
        taskStore.fetchTaskDetail(taskId).then(() => {
          taskStore.fetchTasks()
          chatStore.syncFromTaskDetail()
        })
      },
      onError: () => {
        streamState.value = 'done'
        taskStore.fetchTasks()
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
