import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTaskStore } from './taskStore'
import type { ChatMessage, DisplayArtifact } from '@/types/task'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const taskId = ref<string | null>(null)
  
  const taskStore = useTaskStore()

  const hasConversation = computed(() => messages.value.length > 0)
  
  const lastAssistantMessage = computed(() => {
    const reversed = [...messages.value].reverse()
    return reversed.find(m => m.role === 'assistant') || null
  })

  const currentAssistantMessageIndex = computed(() => {
    for (let i = messages.value.length - 1; i >= 0; i -= 1) {
      if (messages.value[i]?.role === 'assistant') return i
    }
    return -1
  })

  async function loadMessages(newTaskId: string) {
    taskId.value = newTaskId
    await taskStore.fetchTaskDetail(newTaskId)
    syncFromTaskDetail()
  }

  async function addUserMessage(text: string) {
    if (!taskId.value) return

    const tempMessage: ChatMessage = {
      timestamp: new Date().toISOString(),
      role: 'user',
      text,
      source: 'web'
    }
    messages.value.push(tempMessage)

    try {
      const streamUrl = await taskStore.appendInstruction(taskId.value, text)
      return streamUrl
    } catch (e) {
      messages.value.pop()
      throw e
    }
  }

  function addAssistantMessage(text: string) {
    messages.value.push({
      timestamp: new Date().toISOString(),
      role: 'assistant',
      text,
      source: 'bot'
    })
  }

  function clearMessages() {
    messages.value = []
    taskId.value = null
  }

  function syncFromTaskDetail() {
    const serverMessages = taskStore.selectedTaskDetail?.chat_messages
    if (!serverMessages || serverMessages.length === 0) return
    for (const sm of serverMessages) {
      const exists = messages.value.some(
        (m) => m.timestamp === sm.timestamp && m.text === sm.text && m.role === sm.role
      )
      if (!exists) {
        messages.value.push(sm)
      }
    }
    messages.value.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  }

  function artifactsForMessage(index: number): DisplayArtifact[] {
    if (index !== currentAssistantMessageIndex.value) return []
    return taskStore.currentTurnArtifacts
  }

  return {
    messages,
    taskId,
    hasConversation,
    lastAssistantMessage,
    currentAssistantMessageIndex,
    loadMessages,
    addUserMessage,
    addAssistantMessage,
    artifactsForMessage,
    syncFromTaskDetail,
    clearMessages
  }
})
