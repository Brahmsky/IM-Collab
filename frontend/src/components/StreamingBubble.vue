<template>
  <div class="flex w-full justify-start">
    <!-- Assistant Avatar -->
    <div class="flex-shrink-0 mr-3 mt-1">
      <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white shadow-md">
        <span class="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
    </div>

    <!-- Bubble Content -->
    <div class="max-w-[85%]">
      <div class="px-4 py-3 bg-white border border-primary/30 text-text-primary rounded-xl rounded-tl-sm shadow-sm">
        
        <!-- Bouncing Dots (Typing Indicator) -->
        <div v-if="!hasText" class="flex items-center space-x-1 h-6 px-2">
          <div class="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
          <div class="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
          <div class="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
        </div>

        <!-- Streamed Text -->
        <div v-else class="text-[14px] leading-relaxed break-words whitespace-pre-wrap">
          {{ combinedText }}<span class="inline-block w-1.5 h-4 ml-0.5 align-middle bg-primary animate-pulse"></span>
        </div>
      </div>
      <div class="text-[11px] text-primary/70 mt-1 left-1 absolute animate-pulse">
        思考中...
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSseStore } from '@/stores/sseStore'

const sseStore = useSseStore()

const combinedText = computed(() => {
  return sseStore.streamTexts.join('')
})

const hasText = computed(() => {
  return combinedText.value.trim().length > 0
})
</script>
