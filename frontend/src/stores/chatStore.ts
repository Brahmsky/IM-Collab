import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTaskStore } from './taskStore'
import { appendInstruction } from '@/utils/api'
import type { ChatMessage } from '@/types/task'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const taskId = ref<string | null>(null)
  
  const taskStore = useTaskStore()

  const hasConversation = computed(() => messages.value.length > 0)
  
  const lastAssistantMessage = computed(() => {
    const reversed = [...messages.value].reverse()
    return reversed.find(m => m.role === 'assistant') || null
  })

  async function loadMessages(newTaskId: string) {
    taskId.value = newTaskId
    await taskStore.fetchTaskDetail(newTaskId)
    if (taskStore.selectedTaskDetail?.chat_messages) {
      messages.value = [...taskStore.selectedTaskDetail.chat_messages]
    } else {
      messages.value = []
    }
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

  return {
    messages,
    taskId,
    hasConversation,
    lastAssistantMessage,
    loadMessages,
    addUserMessage,
    addAssistantMessage,
    clearMessages
  }
})
