import { ref, computed, watch } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { useSseStore } from '@/stores/sseStore'
import { useChatStore } from '@/stores/chatStore'

export type StateType = 'idle' | 'sending' | 'streaming' | 'completed' | 'failed' | 'waiting' | 'pending_reply'

export function useStateMachine() {
  const taskStore = useTaskStore()
  const sseStore = useSseStore()
  const chatStore = useChatStore()
  
  const currentState = ref<StateType>('idle')

  const isTerminal = computed(() => {
    return ['completed', 'failed', 'waiting', 'pending_reply'].includes(currentState.value)
  })

  const statusLabel = computed(() => {
    switch (currentState.value) {
      case 'idle': return '就绪'
      case 'sending': return '发送中...'
      case 'streaming': return '执行中...'
      case 'completed': return '已完成'
      case 'failed': return '失败'
      case 'waiting': return '等待确认'
      case 'pending_reply': return '有新消息'
      default: return '未知'
    }
  })

  const statusBadge = computed(() => {
    switch (currentState.value) {
      case 'idle': return 'bg-gray-100 text-gray-800'
      case 'sending': return 'bg-blue-100 text-blue-800 animate-pulse'
      case 'streaming': return 'bg-blue-100 text-blue-800 animate-pulse'
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'waiting': return 'bg-yellow-100 text-yellow-800'
      case 'pending_reply': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  })

  function transition(newState: StateType, context?: any) {
    currentState.value = newState
  }

  watch(() => taskStore.selectedTaskDetail, (detail) => {
    if (!detail) {
      transition('idle')
      return
    }

    if (sseStore.isStreaming) {
      transition('streaming')
      return
    }

    if (detail.pending_controls) {
      transition('pending_reply')
      return
    }

    switch (detail.task.state) {
      case 'completed':
        transition('completed')
        break
      case 'failed':
        transition('failed')
        break
      case 'waiting_for_user':
        transition('waiting')
        break
      case 'running':
      case 'queued':
        transition('streaming')
        break
      default:
        transition('idle')
    }
  }, { deep: true, immediate: true })

  watch(() => sseStore.streamState, (state) => {
    if (state === 'connecting' || state === 'streaming') {
      transition('streaming')
    } else if (state === 'done') {
      const taskState = taskStore.selectedTaskDetail?.task.state
      if (taskState === 'completed') transition('completed')
      else if (taskState === 'failed') transition('failed')
      else if (taskState === 'waiting_for_user') transition('waiting')
      else if (taskStore.pendingControls) transition('pending_reply')
    }
  })

  return {
    currentState,
    transition,
    isTerminal,
    statusLabel,
    statusBadge
  }
}
