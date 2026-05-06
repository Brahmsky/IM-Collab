<template>
  <div class="flex flex-col h-full bg-surface">
    <!-- Header -->
    <div class="h-14 flex items-center px-5 border-b border-border shrink-0 bg-surface">
      <div class="flex flex-col">
        <span class="font-medium text-text-primary">智能体交互空间</span>
        <span class="text-[10px] text-text-secondary">Metadata & Artifacts</span>
      </div>
    </div>

    <div v-if="!task" class="flex-1 flex items-center justify-center text-text-secondary text-sm">
      未选择任务
    </div>

    <div v-else class="flex-1 overflow-y-auto p-5 space-y-6">
      
      <!-- Metadata Section -->
      <div class="space-y-3">
        <h3 class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Metadata</h3>
        <div class="bg-background rounded-lg p-3 space-y-2 border border-border">
          
          <div class="flex justify-between items-center">
            <span class="text-xs text-text-secondary">状态</span>
            <span class="text-xs px-2 py-0.5 rounded-full border" :class="getStateBadgeClass(task.state)">
              {{ getStateText(task.state) }}
            </span>
          </div>

          <div class="flex justify-between items-center">
            <span class="text-xs text-text-secondary">创建时间</span>
            <span class="text-xs text-text-primary">{{ formatTime(task.created_at) }}</span>
          </div>

          <div class="flex justify-between items-center" v-if="task.codex_thread_id">
            <span class="text-xs text-text-secondary">Codex Thread</span>
            <span class="text-[10px] font-mono text-text-primary bg-surface border border-border px-1.5 py-0.5 rounded" title="Thread ID">
              {{ truncate(task.codex_thread_id) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Artifacts Section -->
      <div class="space-y-3 pt-2 border-t border-border">
        <h3 class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Artifacts</h3>
        <div v-if="displayArtifacts.length > 0" class="space-y-2">
          <ArtifactCard 
            v-for="item in displayArtifacts" 
            :key="item.id"
            :label="item.title"
            :value="item.value"
            :kind="item.kind"
            :url="item.url"
          />
        </div>
        <p v-else class="text-[13px] text-text-secondary">暂无工件链接</p>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import ArtifactCard from './ArtifactCard.vue'

const taskStore = useTaskStore()
const task = computed(() => taskStore.selectedTaskDetail?.task)

const displayArtifacts = computed(() => taskStore.sessionArtifacts)

const formatTime = (isoString?: string) => {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', { 
    month: 'short', day: 'numeric', 
    hour: '2-digit', minute: '2-digit' 
  })
}

const truncate = (str: string) => {
  if (str.length <= 12) return str
  return `${str.substring(0, 6)}...${str.substring(str.length - 4)}`
}

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
</script>
