<template>
  <div class="flex w-full" :class="isUser ? 'justify-end' : 'justify-start'">
    <!-- Assistant Avatar -->
    <div v-if="!isUser" class="flex-shrink-0 mr-3 mt-1">
      <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
        <span class="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
    </div>

    <!-- Bubble Content -->
    <div 
      class="relative group"
      :class="isUser ? 'max-w-[75%]' : 'max-w-[85%]'"
    >
      <div 
        class="px-4 py-3 text-[14px] leading-relaxed shadow-sm break-words whitespace-pre-wrap"
        :class="isUser 
          ? 'bg-primary text-white rounded-xl rounded-tr-sm' 
          : 'bg-white border border-border text-text-primary rounded-xl rounded-tl-sm'"
      >
        {{ text }}
      </div>
      
      <!-- Timestamp (visible on hover or always subtly) -->
      <div 
        class="text-[11px] text-text-secondary mt-1 absolute"
        :class="isUser ? 'right-1' : 'left-1'"
        v-if="timestamp"
      >
        {{ formatTime(timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  role: 'user' | 'assistant'
  text: string
  timestamp?: string
}>()

const isUser = computed(() => props.role === 'user')

const formatTime = (ts: string) => {
  const date = new Date(ts)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>
