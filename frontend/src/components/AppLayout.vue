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
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/taskStore'
import SessionSidebar from './SessionSidebar.vue'
import ChatPanel from './ChatPanel.vue'
import InspectorPanel from './InspectorPanel.vue'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

onMounted(() => {
  if (route.query.task) {
    taskStore.selectTask(route.query.task as string)
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
