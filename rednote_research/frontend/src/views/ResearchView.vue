<template>
  <div class="research-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">研究进度</h1>
        <p class="page-subtitle">正在分析主题：{{ currentTopic }}</p>
      </div>
    </div>
    
    <!-- 进度指示器 -->
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
    
    <!-- 研究摘要 -->
    <div class="research-summary">
      <div class="summary-card">
        <span class="summary-label">搜索笔记</span>
        <span class="summary-value primary">{{ stats.notesFound }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">分析内容</span>
        <span class="summary-value">{{ stats.contentsAnalyzed }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">提取观点</span>
        <span class="summary-value">{{ stats.insightsExtracted }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">耗时</span>
        <span class="summary-value">{{ formatTime(elapsedTime) }}</span>
      </div>
    </div>
    
    <!-- 日志容器 -->
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
    
    <!-- 控制按钮 -->
    <div class="research-controls">
      <button class="btn btn-secondary" @click="goBack" :disabled="isResearching">
        返回首页
      </button>
      <button 
        v-if="isCompleted" 
        class="btn btn-primary" 
        @click="goToOutline"
      >
        编辑大纲
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResearchStore } from '../stores/research'

const route = useRoute()
const router = useRouter()
const store = useResearchStore()

const logContainer = ref<HTMLElement | null>(null)
const currentTopic = ref('')
const currentStage = ref('planning')
const completedStages = ref<string[]>([])
const isResearching = ref(false)
const isCompleted = ref(false)
const elapsedTime = ref(0)
let timer: number | null = null

const stages = [
  { key: 'planning', label: '规划' },
  { key: 'searching', label: '搜索' },
  { key: 'analyzing', label: '分析' },
  { key: 'generating', label: '生成' }
]

const stats = ref({
  notesFound: 0,
  contentsAnalyzed: 0,
  insightsExtracted: 0
})

interface LogEntry {
  time: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
}

const logs = ref<LogEntry[]>([])

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const addLog = (level: LogEntry['level'], message: string) => {
  const now = new Date()
  logs.value.push({
    time: now.toLocaleTimeString('zh-CN', { hour12: false }),
    level,
    message
  })
  
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

const startResearch = async () => {
  currentTopic.value = route.query.topic as string || ''
  if (!currentTopic.value) {
    router.push('/')
    return
  }
  
  isResearching.value = true
  addLog('info', `开始研究主题: ${currentTopic.value}`)
  
  // 启动计时器
  timer = window.setInterval(() => {
    elapsedTime.value++
  }, 1000)
  
  // 使用 SSE 连接后端
  try {
    const eventSource = new EventSource(`/api/research?topic=${encodeURIComponent(currentTopic.value)}`)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleSSEMessage(data)
      } catch (e) {
        addLog('info', event.data)
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
      if (!isCompleted.value) {
        addLog('error', '连接中断')
        isResearching.value = false
      }
    }
  } catch (error) {
    addLog('error', `研究失败: ${error}`)
    isResearching.value = false
  }
}

const handleSSEMessage = (data: any) => {
  if (data.type === 'log') {
    addLog(data.level || 'info', data.message)
  } else if (data.type === 'stage') {
    if (currentStage.value && !completedStages.value.includes(currentStage.value)) {
      completedStages.value.push(currentStage.value)
    }
    currentStage.value = data.stage
    addLog('success', `进入阶段: ${stages.find(s => s.key === data.stage)?.label}`)
  } else if (data.type === 'stats') {
    stats.value = { ...stats.value, ...data.stats }
  } else if (data.type === 'report') {
    // 填充 store 数据
    store.setTopic(data.topic)
    
    // 设置关键发现
    if (data.insights?.key_findings) {
      store.setKeyFindings(data.insights.key_findings)
    }
    
    // 设置摘要
    if (data.insights?.recommendations) {
      store.setSummary(data.insights.recommendations.join('\n'))
    }
    
    // 设置笔记数据
    if (data.notes) {
      store.setNotes(data.notes)
    }
    
    // 构建大纲
    buildOutlineFromInsights(data.insights, data.notes || [])
    addLog('success', '报告数据已加载')
  } else if (data.type === 'complete') {
    completedStages.value.push(currentStage.value)
    isCompleted.value = true
    isResearching.value = false
    addLog('success', '研究完成！')
    if (timer) {
      clearInterval(timer)
    }
  }
}

// 从 insights 构建大纲
const buildOutlineFromInsights = (insights: any, notes: any[]) => {
  // 清空现有大纲
  store.outline.length = 0
  
  // 封面
  store.addSection('cover', `# ${store.topic}\n\n基于 ${notes.length} 篇小红书笔记的深度研究`)
  
  // 核心发现章节
  if (insights?.key_findings?.length > 0) {
    const findingsContent = insights.key_findings
      .map((f: string, i: number) => `${i + 1}. ${f}`)
      .join('\n')
    store.addSection('content', `## 核心发现\n\n${findingsContent}`)
  }
  
  // 用户痛点章节
  if (insights?.user_pain_points?.length > 0) {
    const painContent = insights.user_pain_points
      .map((p: string) => `- ${p}`)
      .join('\n')
    store.addSection('content', `## 用户痛点\n\n${painContent}`)
  }
  
  // 建议章节
  if (insights?.recommendations?.length > 0) {
    const recContent = insights.recommendations
      .map((r: string) => `- ${r}`)
      .join('\n')
    store.addSection('summary', `## 建议与总结\n\n${recContent}`)
  }
  
  store.markCompleted()
}

const goBack = () => {
  router.push('/')
}

const goToOutline = () => {
  router.push('/outline')
}

onMounted(() => {
  startResearch()
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>
