<template>
  <div class="bg-white border border-border rounded-md shadow-sm overflow-hidden flex flex-col group transition-all hover:border-primary/40 hover:shadow">
    
    <!-- Colored Left Border Effect (using pseudo-element or border-left) -->
    <div class="flex items-stretch border-l-4" :class="borderClass">
      
      <div class="flex-1 p-3 min-w-0">
        <div class="flex items-center justify-between mb-1.5">
          <!-- Kind Badge -->
          <div class="flex items-center space-x-1.5" :class="textClass">
            <span class="material-symbols-outlined text-[16px]">{{ iconName }}</span>
            <span class="text-[10px] font-bold uppercase tracking-wider">{{ kindLabel }}</span>
          </div>
          
          <!-- Pending Indicator -->
          <div v-if="!url && !value" class="flex items-center space-x-1">
            <div class="w-1.5 h-1.5 rounded-full bg-warning animate-pulse"></div>
            <span class="text-[10px] text-warning">待生成</span>
          </div>
        </div>
        
        <!-- Label / Title -->
        <h4 class="text-sm font-medium text-text-primary truncate mb-1" :title="label">
          {{ label }}
        </h4>
        
        <!-- Value / URL -->
        <div v-if="url" class="truncate">
          <a 
            :href="url" 
            target="_blank" 
            rel="noopener noreferrer"
            class="text-xs text-primary hover:text-primary-hover hover:underline inline-flex items-center max-w-full"
            title="点击打开"
          >
            <span class="truncate">{{ url }}</span>
            <span class="material-symbols-outlined text-[12px] ml-1 flex-shrink-0">open_in_new</span>
          </a>
        </div>
        <div v-else-if="value" class="text-xs text-text-secondary truncate" :title="value">
          {{ value }}
        </div>
        
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DisplayArtifactKind } from '@/types/task'

const props = defineProps<{
  label: string
  value?: string
  kind: DisplayArtifactKind
  url?: string
}>()

const iconName = computed(() => {
  switch (props.kind) {
    case 'document': return 'description'
    case 'slides': return 'co_present'
    case 'whiteboard': return 'dashboard'
    case 'sheet': return 'table'
    case 'file': return 'article'
    default: return 'article'
  }
})

const kindLabel = computed(() => {
  switch (props.kind) {
    case 'document': return 'DOCX'
    case 'slides': return 'PPTX'
    case 'whiteboard': return 'BOARD'
    case 'sheet': return 'SHEET'
    case 'file': return 'FILE'
    default: return 'FILE'
  }
})

const borderClass = computed(() => {
  switch (props.kind) {
    case 'document': return 'border-blue-400'
    case 'slides': return 'border-orange-400'
    case 'whiteboard': return 'border-purple-400'
    case 'sheet': return 'border-green-400'
    case 'file': return 'border-gray-400'
    default: return 'border-gray-400'
  }
})

const textClass = computed(() => {
  switch (props.kind) {
    case 'document': return 'text-blue-600'
    case 'slides': return 'text-orange-600'
    case 'whiteboard': return 'text-purple-600'
    case 'sheet': return 'text-green-600'
    case 'file': return 'text-gray-600'
    default: return 'text-gray-600'
  }
})
</script>
