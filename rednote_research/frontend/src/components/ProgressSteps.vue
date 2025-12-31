<template>
  <div class="research-progress">
    <div 
      v-for="(step, index) in stages" 
      :key="step.key"
      class="progress-step"
    >
      <div 
        class="step-icon"
        :class="{ 
          active: currentStage === step.key,
          completed: completedStages.includes(step.key)
        }"
      >
        <span v-if="completedStages.includes(step.key)">✓</span>
        <span v-else>{{ index + 1 }}</span>
      </div>
      <span 
        class="step-label"
        :class="{ 
          active: currentStage === step.key,
          completed: completedStages.includes(step.key)
        }"
      >
        {{ step.label }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'

interface Stage {
  key: string
  label: string
}

defineProps<{
  stages: Stage[]
  currentStage: string
  completedStages: string[]
}>()
</script>
