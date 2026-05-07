<template>
  <div class="flex items-end gap-2 bg-white rounded-xl px-3 py-2 mx-4 mb-3">
    <textarea
      ref="inputRef"
      v-model="text"
      rows="1"
      placeholder="输入指令，Enter 发送"
      class="flex-1 resize-none bg-transparent border-0 outline-none text-[14px] text-text-primary placeholder-text-secondary leading-relaxed"
      @keydown.enter.prevent="handleEnter"
      @input="autoGrow"
    ></textarea>
    <button
      type="button"
      class="shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors relative z-10"
      :class="buttonClass"
      :disabled="buttonDisabled"
      @click="handlePrimaryAction"
    >
      <span class="material-symbols-outlined text-[20px]">{{ buttonIcon }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps<{
  taskId: string
  interruptible?: boolean
  interruptBusy?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', text: string): void
  (e: 'interrupt'): void
}>()

const text = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)

const hasDraft = computed(() => text.value.trim().length > 0)
const showInterrupt = computed(() => !!props.interruptible && !hasDraft.value)

const buttonIcon = computed(() => {
  if (showInterrupt.value) return 'stop_circle'
  return 'send'
})

const buttonDisabled = computed(() => {
  if (showInterrupt.value) return !!props.interruptBusy
  return !hasDraft.value
})

const buttonClass = computed(() => {
  if (showInterrupt.value) {
    return props.interruptBusy
      ? 'bg-[#FFECE8] text-error/40 cursor-not-allowed'
      : 'bg-[#FFECE8] text-error hover:bg-error hover:text-white cursor-pointer shadow-sm'
  }
  return hasDraft.value
    ? 'text-primary hover:bg-tag-bg-blue cursor-pointer'
    : 'text-text-tertiary cursor-not-allowed'
})

const handleEnter = (e: KeyboardEvent) => {
  if (e.shiftKey) {
    text.value += '\n'
    autoGrow()
    return
  }
  if (hasDraft.value) submit()
}

const submit = () => {
  if (!hasDraft.value) return
  emit('submit', text.value.trim())
  text.value = ''
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
      inputRef.value.focus()
    }
  })
}

const handlePrimaryAction = () => {
  if (showInterrupt.value) {
    if (!props.interruptBusy) emit('interrupt')
    return
  }
  submit()
}

const autoGrow = () => {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 128)}px`
}

watch(() => props.taskId, () => {
  nextTick(() => inputRef.value?.focus())
})
</script>
