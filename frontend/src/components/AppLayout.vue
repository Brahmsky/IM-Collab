<template>
  <div class="h-screen w-full flex overflow-hidden">
    <div class="w-[256px] flex-shrink-0 border-r border-border bg-surface">
      <SessionSidebar />
    </div>
    <div class="flex-1 flex flex-col min-w-0">
      <ChatPanel />
    </div>
    <div class="w-[320px] flex-shrink-0 border-l border-border bg-surface">
      <InspectorPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/taskStore'
import { useChatStore } from '@/stores/chatStore'
import { useSseStore } from '@/stores/sseStore'
import SessionSidebar from './SessionSidebar.vue'
import ChatPanel from './ChatPanel.vue'
import InspectorPanel from './InspectorPanel.vue'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const chatStore = useChatStore()
const sseStore = useSseStore()
let refreshTimer: number | null = null

onMounted(() => {
  if (route.query.task) {
    taskStore.selectTask(route.query.task as string)
  }

  refreshTimer = window.setInterval(async () => {
    await taskStore.fetchTasks()
    if (taskStore.selectedTaskId && !sseStore.isStreaming) {
      await taskStore.fetchTaskDetail(taskStore.selectedTaskId)
      chatStore.syncFromTaskDetail()
    }
  }, 3000)
})

onUnmounted(() => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
  }
})

watch(
  () => taskStore.selectedTaskId,
  (newId) => {
    if (newId) {
      router.replace({ query: { ...route.query, task: newId } })
    }
  }
)
</script>
