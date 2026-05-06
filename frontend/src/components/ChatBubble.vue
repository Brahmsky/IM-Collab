<template>
  <div class="flex w-full" :class="isUser ? 'justify-end' : 'justify-start'">
    <div v-if="!isUser" class="flex-shrink-0 mr-3 mt-1">
      <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
        <span class="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
    </div>
    <div 
      class="group"
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

      <!-- Turn Artifacts -->
      <div v-if="artifactList.length > 0" class="mt-3 space-y-2">
        <ArtifactCard
          v-for="artifact in artifactList"
          :key="artifact.id"
          :label="artifact.title"
          :value="artifact.value"
          :kind="artifact.kind"
          :url="artifact.url"
        />
      </div>

      <div 
        v-if="timestamp"
        class="text-[11px] text-text-secondary mt-1"
        :class="isUser ? 'text-right' : 'text-left'"
      >
        {{ formatTime(timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DisplayArtifact } from '@/types/task'
import ArtifactCard from './ArtifactCard.vue'

const props = defineProps<{
  role: 'user' | 'assistant'
  text: string
  timestamp?: string
  artifacts?: DisplayArtifact[]
}>()

const isUser = computed(() => props.role === 'user')

const artifactList = computed(() => props.artifacts ?? [])

const formatTime = (ts: string) => {
  const date = new Date(ts)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>
