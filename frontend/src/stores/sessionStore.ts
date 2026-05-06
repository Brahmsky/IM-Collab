import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { renameSession as apiRenameSession, deleteSession as apiDeleteSession } from '@/utils/api'
import { useTaskStore } from './taskStore'

export const useSessionStore = defineStore('session', () => {
  const openGroups = ref<Record<string, boolean>>({})
  const searchQuery = ref<string>('')
  
  const taskStore = useTaskStore()

  const groupedTasks = computed(() => {
    const groups = taskStore.tasksBySession
    if (!searchQuery.value) return groups

    const query = searchQuery.value.toLowerCase()
    const filteredGroups: Record<string, typeof taskStore.tasks> = {}
    
    for (const [key, tasks] of Object.entries(groups)) {
      const filteredTasks = tasks.filter(t => 
        t.summary.toLowerCase().includes(query) || 
        t.session_title?.toLowerCase().includes(query) ||
        t.chat_name?.toLowerCase().includes(query)
      )
      if (filteredTasks.length > 0) {
        filteredGroups[key] = filteredTasks
      }
    }
    return filteredGroups
  })

  function toggleGroup(sessionKey: string) {
    openGroups.value[sessionKey] = !openGroups.value[sessionKey]
    persistOpenGroups()
  }

  function setSearchQuery(query: string) {
    searchQuery.value = query
  }

  async function renameSession(sessionKey: string, title: string) {
    await apiRenameSession(sessionKey, title)
    await taskStore.fetchTasks()
  }

  async function deleteSession(sessionKey: string) {
    await apiDeleteSession(sessionKey)
    await taskStore.fetchTasks()
  }

  function loadOpenGroups() {
    const stored = localStorage.getItem('im_collab_open_groups')
    if (stored) {
      try {
        openGroups.value = JSON.parse(stored)
      } catch (e) {
        openGroups.value = {}
      }
    }
  }

  function persistOpenGroups() {
    localStorage.setItem('im_collab_open_groups', JSON.stringify(openGroups.value))
  }

  return {
    openGroups,
    searchQuery,
    groupedTasks,
    toggleGroup,
    setSearchQuery,
    renameSession,
    deleteSession,
    loadOpenGroups,
    persistOpenGroups
  }
})
