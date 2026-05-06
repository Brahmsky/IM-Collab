import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchTasks as apiFetchTasks,
  fetchTaskDetail as apiFetchTaskDetail,
  appendInstruction as apiAppendInstruction,
  interruptTask as apiInterruptTask,
  ackTask as apiAckTask,
  retryTask as apiRetryTask
} from '@/utils/api'
import type { TaskSummary, TaskDetailResponse } from '@/types/task'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<TaskSummary[]>([])
  const selectedTaskId = ref<string | null>(null)
  const selectedTaskDetail = ref<TaskDetailResponse | null>(null)
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  const selectedTask = computed(() => {
    if (!selectedTaskId.value) return null
    return tasks.value.find((t) => t.task_id === selectedTaskId.value) || null
  })

  const tasksBySession = computed(() => {
    const groups: Record<string, TaskSummary[]> = {}
    for (const task of tasks.value) {
      const key = task.session_key || task.chat_name || 'unknown'
      if (!groups[key]) groups[key] = []
      groups[key].push(task)
    }
    return groups
  })

  const pendingControls = computed(() => {
    if (!selectedTaskDetail.value) return false
    return selectedTaskDetail.value.pending_controls
  })

  async function fetchTasks() {
    loading.value = true
    error.value = null
    try {
      const res = await apiFetchTasks()
      tasks.value = res.tasks
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch tasks'
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskDetail(taskId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await apiFetchTaskDetail(taskId)
      selectedTaskDetail.value = res
      // Optionally update the task summary in the list if needed
      const index = tasks.value.findIndex(t => t.task_id === taskId)
      if (index !== -1) {
        tasks.value[index] = res.task
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch task details'
    } finally {
      loading.value = false
    }
  }

  async function selectTask(taskId: string) {
    selectedTaskId.value = taskId
    await fetchTaskDetail(taskId)
  }

  async function appendInstruction(taskId: string, text: string) {
    const res = await apiAppendInstruction(taskId, text)
    return res.stream_url
  }

  async function interruptTask(taskId: string) {
    return await apiInterruptTask(taskId)
  }

  async function ackTask(taskId: string, note?: string) {
    return await apiAckTask(taskId, note)
  }

  async function retryTask(taskId: string, publish?: boolean) {
    return await apiRetryTask(taskId, publish)
  }

  return {
    tasks,
    selectedTaskId,
    selectedTaskDetail,
    loading,
    error,
    selectedTask,
    tasksBySession,
    pendingControls,
    fetchTasks,
    fetchTaskDetail,
    selectTask,
    appendInstruction,
    interruptTask,
    ackTask,
    retryTask
  }
})
