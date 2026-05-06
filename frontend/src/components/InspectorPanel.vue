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

      <!-- Action Buttons -->
      <div class="space-y-3 pt-2 border-t border-border">
        <h3 class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Actions</h3>
        
        <div v-if="task.state === 'running'" class="w-full">
          <button 
            @click="handleInterrupt"
            class="w-full py-2 bg-white border border-error text-error hover:bg-error hover:text-white rounded-md transition-colors text-sm font-medium flex items-center justify-center shadow-sm"
          >
            <span class="material-symbols-outlined text-[18px] mr-1">stop_circle</span>
            打断
          </button>
        </div>

        <div v-else-if="task.state === 'waiting_for_user'" class="space-y-3">
          <div class="space-y-2">
            <label class="text-xs text-text-secondary">确认说明 / 补充要求</label>
            <textarea 
              v-model="ackNote"
              placeholder="可以输入补充信息..."
              class="w-full bg-background border border-border focus:border-primary focus:ring-1 focus:ring-primary rounded-md p-2 text-sm text-text-primary outline-none resize-none h-20 transition-all"
            ></textarea>
          </div>
          <div class="flex space-x-2">
            <button 
              @click="handleAck"
              class="flex-1 py-2 bg-primary text-white hover:bg-primary-hover rounded-md transition-colors text-sm font-medium flex items-center justify-center shadow-sm"
            >
              <span class="material-symbols-outlined text-[18px] mr-1">check_circle</span>
              确认并继续
            </button>
            <button 
              @click="handleRetry"
              class="px-3 py-2 bg-white border border-border text-text-primary hover:bg-surface-hover rounded-md transition-colors text-sm font-medium flex items-center justify-center shadow-sm"
              title="重新执行"
            >
              <span class="material-symbols-outlined text-[18px]">refresh</span>
            </button>
          </div>
        </div>

        <div v-else-if="taskStore.pendingControls" class="w-full">
          <button 
            @click="handleRetry"
            class="w-full py-2 bg-primary text-white hover:bg-primary-hover rounded-md transition-colors text-sm font-medium flex items-center justify-center shadow-sm"
          >
            <span class="material-symbols-outlined text-[18px] mr-1">play_arrow</span>
            执行补充
          </button>
        </div>

        <div v-else-if="['completed', 'failed'].includes(task.state)" class="w-full">
          <button 
            @click="handleRetry"
            class="w-full py-2 bg-white border border-border text-text-primary hover:bg-surface-hover rounded-md transition-colors text-sm font-medium flex items-center justify-center shadow-sm"
          >
            <span class="material-symbols-outlined text-[18px] mr-1">refresh</span>
            重试
          </button>
        </div>
      </div>

      <!-- Artifacts Section -->
      <div v-if="hasArtifacts" class="space-y-3 pt-2 border-t border-border">
        <h3 class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Artifacts</h3>
        <div class="space-y-2">
          <ArtifactCard 
            v-for="(item, idx) in taskStore.selectedTaskDetail?.artifacts?.items" 
            :key="idx"
            :label="item.title || 'Untitled'"
            :value="item.remote?.url || item.path || ''"
            :kind="inferKind(item)"
            :url="item.remote?.url"
          />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import ArtifactCard from './ArtifactCard.vue'

const taskStore = useTaskStore()
const task = computed(() => taskStore.selectedTaskDetail?.task)

const ackNote = ref('')

const hasArtifacts = computed(() => {
  return taskStore.selectedTaskDetail?.artifacts?.items && taskStore.selectedTaskDetail.artifacts.items.length > 0
})

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

const inferKind = (item: any): 'document' | 'slides' | 'whiteboard' | 'file' => {
  if (item.kind) {
    if (['document', 'slides', 'whiteboard', 'file'].includes(item.kind)) {
      return item.kind as any
    }
  }
  const url = item.remote?.url || ''
  const title = item.title || ''
  
  if (url.includes('docx') || title.includes('文档') || title.includes('docx')) return 'document'
  if (url.includes('slides') || title.includes('PPT') || title.includes('幻灯片')) return 'slides'
  if (url.includes('board') || title.includes('白板')) return 'whiteboard'
  return 'file'
}

// Actions
const handleInterrupt = async () => {
  if (!task.value) return
  await taskStore.interruptTask(task.value.task_id)
  await taskStore.fetchTasks()
  await taskStore.fetchTaskDetail(task.value.task_id)
}

const handleAck = async () => {
  if (!task.value) return
  await taskStore.ackTask(task.value.task_id, ackNote.value)
  ackNote.value = ''
  await taskStore.fetchTasks()
  await taskStore.fetchTaskDetail(task.value.task_id)
}

const handleRetry = async () => {
  if (!task.value) return
  await taskStore.retryTask(task.value.task_id)
  await taskStore.fetchTasks()
  await taskStore.fetchTaskDetail(task.value.task_id)
}
</script>
