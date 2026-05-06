<template>
  <div class="relative bg-white rounded-xl border border-border shadow-sm focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all">
    <div class="flex items-end p-2">
      <!-- Visual Attach Icon (Disabled) -->
      <button 
        type="button"
        class="p-2 text-text-secondary hover:text-primary transition-colors mb-1 rounded-full hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed"
        disabled
        title="暂不支持上传附件"
      >
        <span class="material-symbols-outlined text-[20px]">attach_file</span>
      </button>

      <!-- Auto-growing Textarea -->
      <textarea
        ref="inputRef"
        v-model="text"
        :disabled="disabled"
        placeholder="输入追加指令，Enter 发送，Shift + Enter 换行..."
        class="flex-1 max-h-32 min-h-[40px] p-2 bg-transparent resize-none outline-none text-[14px] text-text-primary disabled:cursor-not-allowed placeholder-text-secondary"
        @keydown.enter.prevent="handleEnter"
        @input="autoGrow"
      ></textarea>

      <!-- Send Button -->
      <button 
        type="button"
        class="p-2 ml-2 mb-1 rounded-full transition-colors flex items-center justify-center"
        :class="canSubmit 
          ? 'bg-primary text-white hover:bg-primary-hover shadow-md' 
          : 'bg-surface-hover text-text-secondary cursor-not-allowed'"
        :disabled="!canSubmit"
        @click="submit"
      >
        <span class="material-symbols-outlined text-[18px]">send</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps<{
  taskId: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', text: string): void
}>()

const text = ref('')
const inputRef = ref<HTMLTextAreaElement | null>(null)

const canSubmit = computed(() => {
  return !props.disabled && text.value.trim().length > 0
})

const handleEnter = (e: KeyboardEvent) => {
  if (e.shiftKey) {
    // Let default behavior happen (newline)
    text.value += '\n'
    autoGrow()
    return
  }
  
  if (canSubmit.value) {
    submit()
  }
}

const submit = () => {
  if (!canSubmit.value) return
  
  emit('submit', text.value.trim())
  text.value = ''
  
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
      inputRef.value.focus()
    }
  })
}

const autoGrow = () => {
  const el = inputRef.value
  if (!el) return
  
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 128)}px`
}

// Auto-focus when task changes and not disabled
watch(() => props.taskId, () => {
  if (!props.disabled) {
    nextTick(() => {
      inputRef.value?.focus()
    })
  }
})
</script>
