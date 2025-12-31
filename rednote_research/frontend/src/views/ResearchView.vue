<template>
  <div class="research-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">研究进度</h1>
        <p class="page-subtitle">正在分析主题：{{ activeTaskStore.topic }}</p>
      </div>
    </div>
    
    <!-- 进度指示器 -->
    <ProgressSteps 
      :stages="stages"
      :currentStage="activeTaskStore.stage"
      :completedStages="activeTaskStore.completedStages"
    />
    
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
    <LogTerminal :logs="activeTaskStore.logs" />
    
    <!-- 控制按钮 -->
    <div class="research-controls">
      <button class="btn btn-secondary" @click="goBack">
        返回首页
      </button>
      <button 
        v-if="activeTaskStore.isRunning" 
        class="btn btn-danger" 
        @click="stopTask"
      >
        停止任务
      </button>
      <button 
        v-if="isCompleted || activeTaskStore.hasCompletedTask" 
        class="btn btn-primary" 
        @click="goToOutline"
      >
        编辑大纲
      </button>
      <div class="export-group" v-if="isCompleted || activeTaskStore.hasCompletedTask">
         <button class="btn btn-secondary" @click="exportReport('markdown')" :disabled="exporting">
          ⬇️ Markdown
        </button>
        <button class="btn btn-secondary" @click="exportReport('pdf')" :disabled="exporting">
          ⬇️ PDF
        </button>
      </div>
    </div>
    
    <!-- 停止任务确认弹窗 -->
    <div v-if="showStopDialog" class="dialog-overlay" @click.self="showStopDialog = false">
      <div class="dialog-box">
        <div class="dialog-icon">⚠️</div>
        <h3 class="dialog-title">确认停止任务？</h3>
        <p class="dialog-message">
          停止后当前研究将中断，已收集的数据将保留。
        </p>
        <div class="dialog-actions">
          <button class="dialog-btn secondary" @click="showStopDialog = false">
            取消
          </button>
          <button class="dialog-btn danger" @click="confirmStopTask">
            确认停止
          </button>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResearchStore } from '../stores/research'
import { useActiveTaskStore } from '../stores/activeTask'
import ProgressSteps from '../components/ProgressSteps.vue'
import LogTerminal from '../components/LogTerminal.vue'

const route = useRoute()
const router = useRouter()
const store = useResearchStore()
const activeTaskStore = useActiveTaskStore()

const publishing = ref(false)
const exporting = ref(false)

const exportReport = async (format: 'markdown' | 'pdf') => {
  exporting.value = true
  try {
    const response = await axios.post('/api/export', {
      format,
      topic: store.topic,
      insights: { key_findings: store.keyFindings },
      outline: store.outline.map(s => ({ title: s.title, content: s.content, images: s.images })),
      notes: store.notes
    }, {
      responseType: 'blob'
    })
    
    // Download file
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const ext = format === 'markdown' ? 'md' : 'pdf'
    link.setAttribute('download', `${store.topic}_report.${ext}`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (e) {
    console.error('Export failed:', e)
    alert('导出失败')
  } finally {
    exporting.value = false
  }
}

const publishContent = () => {} // Placeholder for the actual publishContent function

const isCompleted = ref(false)
const showStopDialog = ref(false)
let timer: number | null = null

// SSE 重连配置
const SSE_MAX_RETRIES = 5
const SSE_INITIAL_RETRY_DELAY = 1000 // 1秒
const SSE_MAX_RETRY_DELAY = 30000 // 最大30秒

let eventSource: EventSource | null = null
let retryCount = ref(0)
let retryTimeout: number | null = null
let currentTopic = ''

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

// 计算重连延迟（指数退避）
const getRetryDelay = (attempt: number): number => {
  const delay = Math.min(
    SSE_INITIAL_RETRY_DELAY * Math.pow(2, attempt),
    SSE_MAX_RETRY_DELAY
  )
  // 添加随机抖动 (±20%)
  return delay * (0.8 + Math.random() * 0.4)
}

// SSE 连接函数
const connectSSE = (topic: string) => {
  if (eventSource) {
    eventSource.close()
  }
  
  currentTopic = topic
  
  try {
    eventSource = new EventSource(`/api/research?topic=${encodeURIComponent(topic)}`)
    
    eventSource.onopen = () => {
      // 连接成功，重置重试计数
      if (retryCount.value > 0) {
        activeTaskStore.addLog('success', `重连成功 (第${retryCount.value}次尝试)`)
      }
      retryCount.value = 0
    }
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleSSEMessage(data)
      } catch (e) {
        activeTaskStore.addLog('info', event.data)
      }
    }
    
    eventSource.onerror = () => {
      eventSource?.close()
      eventSource = null
      
      if (isCompleted.value) {
        return // 任务已完成，无需重连
      }
      
      // 尝试重连
      if (retryCount.value < SSE_MAX_RETRIES) {
        const delay = getRetryDelay(retryCount.value)
        retryCount.value++
        activeTaskStore.addLog('warning', `连接中断，${(delay / 1000).toFixed(1)}秒后重试 (${retryCount.value}/${SSE_MAX_RETRIES})`)
        
        retryTimeout = window.setTimeout(() => {
          if (!isCompleted.value && currentTopic) {
            connectSSE(currentTopic)
          }
        }, delay)
      } else {
        // 达到最大重试次数
        activeTaskStore.addLog('error', `重连失败已达最大次数 (${SSE_MAX_RETRIES})，请检查网络后刷新页面`)
        activeTaskStore.markCompleted()
        if (timer) {
          clearInterval(timer)
          timer = null
        }
      }
    }
  } catch (error) {
    activeTaskStore.addLog('error', `建立连接失败: ${error}`)
    activeTaskStore.markCompleted()
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }
}

// 清理 SSE 连接
const cleanupSSE = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  if (retryTimeout) {
    clearTimeout(retryTimeout)
    retryTimeout = null
  }
}

const startResearch = async () => {
  const topicParam = route.query.topic as string || ''
  
  // 如果已有进行中任务且没有新的topic参数，恢复显示现有任务
  if (activeTaskStore.isRunning && !topicParam) {
    // elapsedTime 是基于 startTime 的 computed 属性
    // 启动定时器触发UI刷新
    timer = window.setInterval(() => {
      activeTaskStore.updateTick()
    }, 1000)
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
  
  // 使用带重连机制的 SSE 连接
  retryCount.value = 0
  connectSSE(topicParam)
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

const stopTask = () => {
  // 显示确认弹窗
  showStopDialog.value = true
}

const confirmStopTask = () => {
  showStopDialog.value = false
  // 停止任务
  cleanupSSE()
  activeTaskStore.addLog('warning', '用户主动停止任务')
  activeTaskStore.markCompleted()
  if (timer) {
    clearInterval(timer)
    timer = null
  }
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
  cleanupSSE()
  if (timer) {
    clearInterval(timer)
  }
})
</script>

