<template>
  <div class="flex flex-col h-full bg-background relative">
    <!-- Header -->
    <div class="h-14 flex flex-shrink-0 items-center justify-between px-6 bg-surface border-b border-border shadow-sm z-10">
      <div class="flex items-center space-x-3 truncate">
        <h2 class="text-lg font-medium text-text-primary truncate">
          {{ taskTitle }}
        </h2>
        <span 
          v-if="taskStore.selectedTask"
          class="text-xs px-2 py-0.5 rounded-full border"
          :class="getStateBadgeClass(taskStore.selectedTask.state)"
        >
          {{ getStateText(taskStore.selectedTask.state) }}
        </span>
      </div>
    </div>

    <!-- Chat Area -->
    <div 
      class="flex-1 overflow-y-auto p-6 space-y-6"
      data-chat-scroll-container
      ref="scrollContainer"
    >
      <div v-if="!taskStore.selectedTask" class="h-full flex items-center justify-center text-text-secondary">
        请在左侧选择一个会话
      </div>
      
      <template v-else>
        <!-- Empty State / Initial Request -->
        <div v-if="chatStore.messages.length === 0" class="flex justify-center mt-10">
          <div class="max-w-2xl text-center space-y-4">
            <div class="w-16 h-16 mx-auto bg-tag-bg-blue text-primary rounded-full flex items-center justify-center mb-4">
              <span class="material-symbols-outlined text-3xl">flight_takeoff</span>
            </div>
            <h3 class="text-xl font-medium text-text-primary">新任务已就绪</h3>
            <p class="text-text-secondary bg-surface p-4 rounded-lg border border-border text-left shadow-sm">
              {{ taskStore.selectedTask?.summary || '等待接收指令...' }}
            </p>
          </div>
        </div>

        <!-- Messages -->
        <div v-for="(msg, idx) in chatStore.messages" :key="idx">
          <ChatBubble :role="msg.role" :text="msg.text" :timestamp="msg.timestamp" />
        </div>

        <!-- Streaming Indicator -->
        <div v-if="sseStore.isStreaming">
          <StreamingBubble />
        </div>

        <!-- Pending Marker -->
        <div v-if="taskStore.pendingControls && !sseStore.isStreaming">
          <PendingReplyMarker />
        </div>
      </template>
    </div>

    <!-- Bottom Input Area -->
    <div class="p-4 bg-background border-t border-border shrink-0">
      <div class="max-w-4xl mx-auto">
        <AppendForm 
          v-if="taskStore.selectedTaskId"
          :taskId="taskStore.selectedTaskId"
          :disabled="sseStore.isStreaming || !taskStore.selectedTask"
          @submit="handleAppend"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { useChatStore } from '@/stores/chatStore'
import { useSseStore } from '@/stores/sseStore'
import ChatBubble from './ChatBubble.vue'
import StreamingBubble from './StreamingBubble.vue'
import PendingReplyMarker from './PendingReplyMarker.vue'
import AppendForm from './AppendForm.vue'

const taskStore = useTaskStore()
const chatStore = useChatStore()
const sseStore = useSseStore()

const scrollContainer = ref<HTMLElement | null>(null)

const taskTitle = computed(() => {
  const task = taskStore.selectedTask
  if (!task) return '未选择任务'
  return task.chat_name || task.session_title || task.task_id
})

const getStateBadgeClass = (state: string) => {
  switch (state) {
    case 'running': return 'bg-tag-bg-blue text-primary border-primary/20'
    case 'completed': return 'bg-[#E8F8F2] text-success border-success/20'
    case 'failed': return 'bg-[#FFECE8] text-error border-error/20'
    case 'waiting_for_user': return 'bg-[#FFF2E5] text-warning border-warning/20'
    case 'pending_reply': return 'bg-tag-bg-gray text-text-secondary border-border'
    default: return 'bg-tag-bg-gray text-text-secondary border-border'
  }
}

const getStateText = (state: string) => {
  switch (state) {
    case 'running': return '运行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    case 'waiting_for_user': return '待确认'
    case 'pending_reply': return '待回复'
    case 'queued': return '排队中'
    default: return state
  }
}

const handleAppend = async (text: string) => {
  if (!taskStore.selectedTaskId) return
  try {
    await chatStore.addUserMessage(text)
    sseStore.connectStream(taskStore.selectedTaskId)
  } catch (e) {
    console.error('Failed to append instruction', e)
  }
}

// Auto-scroll logic
const scrollToBottom = () => {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
}

watch(() => chatStore.messages.length, scrollToBottom)
watch(() => sseStore.streamTexts.length, scrollToBottom)
watch(() => taskStore.selectedTaskId, () => {
  setTimeout(scrollToBottom, 100)
})
</script>
