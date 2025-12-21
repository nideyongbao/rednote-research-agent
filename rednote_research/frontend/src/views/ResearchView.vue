<template>
  <div class="research-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">研究进度</h1>
        <p class="page-subtitle">正在分析主题：{{ activeTaskStore.topic }}</p>
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
            active: activeTaskStore.stage === step.key,
            completed: activeTaskStore.completedStages.includes(step.key)
          }"
        >
          <span v-if="activeTaskStore.completedStages.includes(step.key)">✓</span>
          <span v-else>{{ index + 1 }}</span>
        </div>
        <span 
          class="step-label"
          :class="{ 
            active: activeTaskStore.stage === step.key,
            completed: activeTaskStore.completedStages.includes(step.key)
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
        <span class="summary-value primary">{{ activeTaskStore.stats.notesFound }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">分析内容</span>
        <span class="summary-value">{{ activeTaskStore.stats.contentsAnalyzed }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">提取观点</span>
        <span class="summary-value">{{ activeTaskStore.stats.insightsExtracted }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">耗时</span>
        <span class="summary-value">{{ formatTime(activeTaskStore.elapsedTime) }}</span>
      </div>
    </div>
    
    <!-- 日志容器 -->
    <div class="log-container" ref="logContainer">
      <div 
        v-for="(log, index) in activeTaskStore.logs" 
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
      <button class="btn btn-secondary" @click="goBack">
        返回首页
      </button>
      <button 
        v-if="isCompleted || activeTaskStore.hasCompletedTask" 
        class="btn btn-primary" 
        @click="goToOutline"
      >
        编辑大纲
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResearchStore } from '../stores/research'
import { useActiveTaskStore } from '../stores/activeTask'

const route = useRoute()
const router = useRouter()
const store = useResearchStore()
const activeTaskStore = useActiveTaskStore()

const logContainer = ref<HTMLElement | null>(null)
const isCompleted = ref(false)
let timer: number | null = null

const stages = [
  { key: 'planning', label: '规划' },
  { key: 'searching', label: '搜索' },
  { key: 'analyzing', label: '分析' },
  { key: 'generating', label: '生成' }
]

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 滚动到日志底部
const scrollToBottom = () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

// 监听日志变化
watch(() => activeTaskStore.logs.length, scrollToBottom)

const startResearch = async () => {
  const topicParam = route.query.topic as string || ''
  
  // 如果已有进行中任务且没有新的topic参数，恢复显示现有任务
  if (activeTaskStore.isRunning && !topicParam) {
    // elapsedTime 是基于 startTime 的 computed 属性
    // 启动定时器触发UI刷新
    timer = window.setInterval(() => {
      activeTaskStore.updateTick()
    }, 1000)
    scrollToBottom()
    return
  }
  
  // 如果没有topic且没有进行中任务，返回首页
  if (!topicParam) {
    router.push('/')
    return
  }
  
  // 开始新任务（startTask会记录开始时间戳）
  activeTaskStore.startTask(topicParam)
  activeTaskStore.addLog('info', `开始研究主题: ${topicParam}`)
  
  // 启动定时器触发UI刷新
  timer = window.setInterval(() => {
    activeTaskStore.updateTick()
  }, 1000)
  
  // 使用 SSE 连接后端
  try {
    const eventSource = new EventSource(`/api/research?topic=${encodeURIComponent(topicParam)}`)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleSSEMessage(data)
      } catch (e) {
        activeTaskStore.addLog('info', event.data)
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
      if (!isCompleted.value) {
        activeTaskStore.addLog('error', '连接中断')
      }
    }
  } catch (error) {
    activeTaskStore.addLog('error', `研究失败: ${error}`)
  }
}

const handleSSEMessage = (data: any) => {
  if (data.type === 'log') {
    activeTaskStore.addLog(data.level || 'info', data.message)
  } else if (data.type === 'stage') {
    activeTaskStore.setStage(data.stage)
    activeTaskStore.addLog('success', `进入阶段: ${stages.find(s => s.key === data.stage)?.label}`)
  } else if (data.type === 'stats') {
    activeTaskStore.updateStats(data.stats)
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
    
    // 优先使用后端返回的结构化大纲
    if (data.outline && data.outline.length > 0) {
      loadOutlineFromBackend(data.outline)
      activeTaskStore.addLog('success', `加载了 ${data.outline.length} 个结构化章节`)
    } else {
      // 回退：从 insights 构建大纲
      buildOutlineFromInsights(data.insights, data.notes || [])
      activeTaskStore.addLog('success', '报告数据已加载')
    }
  } else if (data.type === 'complete') {
    // 标记最后阶段完成
    if (activeTaskStore.stage && !activeTaskStore.completedStages.includes(activeTaskStore.stage)) {
      activeTaskStore.completedStages.push(activeTaskStore.stage)
    }
    
    isCompleted.value = true
    activeTaskStore.addLog('success', '研究完成！点击"编辑大纲"继续')
    
    // 标记任务完成，但保留日志供用户查看
    activeTaskStore.markCompleted()
    
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }
}

// 从后端结构化大纲加载到 store
const loadOutlineFromBackend = (outline: any[]) => {
  // 清空现有大纲
  store.outline.length = 0
  
  for (const section of outline) {
    // 添加章节到 store
    store.addSection(
      section.type || 'content',
      section.content || ''
    )
    // 更新标题和图片
    const lastSection = store.outline[store.outline.length - 1]
    if (lastSection) {
      lastSection.title = section.title || ''
      lastSection.images = section.images || []
    }
  }
  
  store.markCompleted()
}

// 从 insights 构建大纲（备用方案）
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
  // 进入编辑页面时清空任务状态
  activeTaskStore.clearTask()
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
