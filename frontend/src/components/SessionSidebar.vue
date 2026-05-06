<template>
  <div class="flex flex-col h-full bg-surface">
    <!-- Header -->
    <div class="h-14 flex items-center px-4 border-b border-border shrink-0">
      <span class="material-symbols-outlined text-primary mr-2">flight_takeoff</span>
      <span class="font-semibold text-text-primary text-base">Agent-Pilot</span>
    </div>

    <!-- Search -->
    <div class="p-3 shrink-0">
      <div class="relative">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary text-sm">search</span>
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="搜索会话..."
          class="w-full bg-background border border-transparent focus:bg-white focus:border-primary focus:ring-1 focus:ring-primary rounded-md py-1.5 pl-8 pr-3 text-sm text-text-primary outline-none transition-colors"
        >
      </div>
    </div>

    <!-- Session List -->
    <div class="flex-1 overflow-y-auto px-2 pb-4 space-y-4">
      <div v-if="filteredGroups.length === 0" class="text-center mt-10 text-sm text-text-secondary">
        暂无会话分组
      </div>

      <div v-for="group in filteredGroups" :key="group.id" class="space-y-1">
        <div 
          class="flex items-center justify-between px-2 py-1.5 cursor-pointer text-text-primary hover:bg-surface-hover rounded-md group/header"
          @click="toggleGroup(group.id)"
        >
          <span class="min-w-0 flex items-center gap-2">
            <span class="material-symbols-outlined text-[20px] text-text-primary">group</span>
            <span class="text-[13px] font-medium truncate">{{ group.name }}</span>
          </span>
          <span class="material-symbols-outlined text-[16px] text-text-secondary transition-transform shrink-0" :class="{ 'rotate-180': isExpanded(group.id) }">
            expand_more
          </span>
        </div>

        <div v-show="isExpanded(group.id)" class="ml-[22px] border-l border-border pl-3 space-y-0.5">
          <div 
            v-for="task in group.tasks" 
            :key="task.task_id"
            @click="selectTask(task.task_id)"
            class="group relative flex flex-col p-2 rounded-md cursor-pointer transition-colors"
            :class="taskStore.selectedTaskId === task.task_id ? 'bg-tag-bg-blue' : 'hover:bg-surface-hover'"
          >
            <div class="flex items-center justify-between mb-1">
              <div v-if="editingTaskId === task.task_id" class="flex-1 mr-2" @click.stop>
                <input 
                  ref="editInput"
                  v-model="editTitle"
                  @blur="saveTitle(task)"
                  @keyup.enter="saveTitle(task)"
                  @keyup.esc="cancelEdit"
                  class="w-full text-sm border border-primary rounded px-1 py-0.5 outline-none"
                >
              </div>
              <div v-else class="text-sm text-text-primary font-medium truncate flex-1 pr-2">
                {{ getTitle(task) }}
              </div>
              
              <!-- Hover Menu -->
              <div class="hidden group-hover:flex items-center absolute right-2 top-2 bg-surface-hover shadow-sm rounded border border-border">
                <button @click.stop="startEdit(task)" class="p-1 hover:text-primary text-text-secondary" title="重命名">
                  <span class="material-symbols-outlined text-[14px]">edit</span>
                </button>
                <button @click.stop="deleteTask(task.task_id)" class="p-1 hover:text-error text-text-secondary" title="删除">
                  <span class="material-symbols-outlined text-[14px]">delete</span>
                </button>
              </div>
            </div>
            
            <div class="flex items-center justify-between">
              <span class="text-[11px] text-text-secondary">{{ formatTime(task.created_at) }}</span>
              <span 
                class="text-[10px] px-1.5 py-0.5 rounded-sm"
                :class="getStateBadgeClass(task.state)"
              >
                {{ getStateText(task.state) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useSessionStore } from '@/stores/sessionStore'
import { useTaskStore } from '@/stores/taskStore'
import type { TaskSummary } from '@/types/task'

const sessionStore = useSessionStore()
const taskStore = useTaskStore()

const searchQuery = ref('')
const editingTaskId = ref<string | null>(null)
const editTitle = ref('')
const editInput = ref<any>(null)

const isExpanded = (groupId: string) => {
  return !!sessionStore.openGroups[groupId]
}

const toggleGroup = (groupId: string) => {
  sessionStore.toggleGroup(groupId)
}

const selectTask = (taskId: string) => {
  taskStore.selectTask(taskId)
}

const startEdit = (task: TaskSummary) => {
  editingTaskId.value = task.task_id
  editTitle.value = getTitle(task)
  nextTick(() => {
    if (editInput.value && Array.isArray(editInput.value) && editInput.value.length > 0) {
      editInput.value[0].focus()
    } else if (editInput.value) {
      (editInput.value as any).focus()
    }
  })
}

const saveTitle = async (task: TaskSummary) => {
  if (!editingTaskId.value) return
  const newTitle = editTitle.value.trim()
  if (newTitle && newTitle !== getTitle(task) && task.session_key) {
    await sessionStore.renameSession(task.session_key, newTitle)
  }
  editingTaskId.value = null
}

const cancelEdit = () => {
  editingTaskId.value = null
}

const deleteTask = async (taskId: string) => {
  if (!confirm('确定要删除这个任务吗？')) return
  const task = taskStore.tasks.find(t => t.task_id === taskId)
  if (task?.session_key) {
    await sessionStore.deleteSession(task.session_key)
  } else {
    if (taskStore.selectedTaskId === taskId) {
      taskStore.selectedTaskId = null
    }
  }
}

const getTitle = (task: TaskSummary) => {
  return task.session_title || task.chat_name || task.task_id
}

const formatTime = (isoString?: string) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const seconds = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000))
  if (seconds < 60) return '刚刚'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  return `${days} 天前`
}

const getStateBadgeClass = (state: string) => {
  switch (state) {
    case 'running': return 'bg-tag-bg-blue text-primary'
    case 'completed': return 'bg-[#E8F8F2] text-success'
    case 'failed': return 'bg-[#FFECE8] text-error'
    case 'waiting_for_user': return 'bg-[#FFF2E5] text-warning'
    case 'pending_reply': return 'bg-tag-bg-gray text-text-secondary'
    default: return 'bg-tag-bg-gray text-text-secondary'
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

const filteredGroups = computed(() => {
  const groups: { id: string, name: string, tasks: TaskSummary[] }[] = []
  for (const [key, tasks] of Object.entries(sessionStore.groupedTasks)) {
    const name = tasks[0]?.chat_name || tasks[0]?.session_title || key
    groups.push({ id: key, name, tasks })
  }
  return groups
})
</script>
