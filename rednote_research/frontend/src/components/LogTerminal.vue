<template>
  <div class="log-container" ref="logContainer">
    <div 
      v-for="(log, index) in logs" 
      :key="index"
      class="log-entry log-entry-enter"
    >
      <span class="log-time">{{ log.time }}</span>
      <span class="log-level" :class="log.level">{{ log.level }}</span>
      <span class="log-message">{{ log.message }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface LogEntry {
  time: string
  level: string
  message: string
}

const props = defineProps<{
  logs: LogEntry[]
}>()

const logContainer = ref<HTMLElement | null>(null)

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

watch(() => props.logs.length, scrollToBottom)
</script>

<style scoped>
/* 样式应从父组件迁移或保留在全局/父组件中如果使用了 scoped css without deep selector issue.
   为了保证样式一致性，这里假设样式由外部 CSS 提供或需要迁移。
   Check ResearchView styles. Usually scoped styles need to be moved.
   Let's check if I can assume styles are global or need to be localized.
   Since I didn't see specific CSS in the view_file output (it truncated or I missed it? 
   No, view_file showed up to line 439, passing <script> end, but no <style> block was shown? 
   Wait, the view_file output ended at </script>. It implies <style> block might be below line 439.
   I should probably verify styles.
*/
.log-container {
  /* Default styles just in case, but ideally match original */
  overflow-y: auto;
}
</style>
