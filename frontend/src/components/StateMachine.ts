import { computed } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { useSseStore } from '@/stores/sseStore'

export type StateType = 'idle' | 'sending' | 'streaming' | 'completed' | 'failed' | 'waiting' | 'pending_reply'

export function useStateMachine() {
  const taskStore = useTaskStore()
  const sseStore = useSseStore()

  const currentState = computed<StateType>(() => {
    const task = taskStore.selectedTask
    if (!task) return 'idle'

    if (sseStore.isStreaming) return 'streaming'
    if (sseStore.streamState === 'connecting') return 'sending'

    if (taskStore.pendingControls) return 'pending_reply'

    switch (task.state) {
      case 'completed': return 'completed'
      case 'failed': return 'failed'
      case 'waiting_for_user': return 'waiting'
      case 'running': return 'streaming'
      case 'queued': return 'idle'
      default: return 'idle'
    }
  })

  const isTerminal = computed(() =>
    ['completed', 'failed', 'waiting', 'pending_reply'].includes(currentState.value)
  )

  const statusLabel = computed(() => {
    switch (currentState.value) {
      case 'idle': return '就绪'
      case 'sending': return '发送中...'
      case 'streaming': return '执行中'
      case 'completed': return '已完成'
      case 'failed': return '失败'
      case 'waiting': return '等待确认'
      case 'pending_reply': return '待回复'
      default: return currentState.value
    }
  })

  const statusBadge = computed(() => {
    switch (currentState.value) {
      case 'sending':
      case 'streaming': return 'bg-tag-bg-blue text-primary'
      case 'completed': return 'bg-[#E8F8F2] text-success'
      case 'failed': return 'bg-[#FFECE8] text-error'
      case 'waiting': return 'bg-[#FFF2E5] text-warning'
      case 'pending_reply': return 'bg-tag-bg-gray text-text-secondary'
      default: return 'bg-tag-bg-gray text-text-secondary'
    }
  })

  return { currentState, isTerminal, statusLabel, statusBadge }
}
