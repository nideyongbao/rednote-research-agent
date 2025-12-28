<template>
  <div class="home-view">
    <!-- 图片网格轮播背景 -->
    <ShowcaseBackground />
    
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <div class="brand-pill">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
          </svg>
          AI 驱动的小红书研究助手
        </div>
        <div class="platform-slogan">
          让研究不再需要门槛，让洞察从未如此简单
        </div>
        <h1 class="search-title">灵感一触即发</h1>
        <p class="search-subtitle">
          输入研究主题，AI 将自动搜索、分析小红书笔记，为您生成专业研究报告
        </p>
      </div>
      
      <div class="search-box">
        <input
          v-model="topic"
          type="text"
          class="search-input"
          placeholder="输入您想研究的主题，如：咖啡店创业、护肤心得、旅行攻略..."
          @keyup.enter="startResearch"
        />
        <button 
          class="search-btn" 
          :disabled="!topic.trim() || isLoading"
          @click="startResearch"
        >
          <span v-if="isLoading" class="spinner"></span>
          <span v-else>开始研究</span>
        </button>
      </div>
      
      <div class="hot-topics">
        <div class="topics-title">🔥 热门话题推荐</div>
        <div class="tag-cloud">
          <span 
            v-for="tag in hotTags" 
            :key="tag" 
            class="tag"
            @click="selectTag(tag)"
          >
            {{ tag }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- 进行中任务入口（仅进行中显示，完成后消失）-->
    <div v-if="activeTaskStore.hasActiveTask" class="active-task-section">
      <div class="active-task-card">
        <div class="task-icon" @click="goToResearch">
          <span class="icon-spinning">🔄</span>
        </div>
        <div class="task-info" @click="goToResearch">
          <div class="task-status">进行中</div>
          <div class="task-topic">{{ activeTaskStore.topic }}</div>
          <div class="task-meta">
            <span class="task-stage">{{ getStageName(activeTaskStore.stage) }}</span>
            <span class="task-time">{{ formatTime(activeTaskStore.elapsedTime) }}</span>
          </div>
        </div>
        <div class="task-actions">
          <button class="task-btn" @click="goToResearch">
            查看进度
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="cancel-btn" @click.stop="cancelTask" title="取消任务">
            ✕
          </button>
        </div>
      </div>
    </div>
    
    <!-- 任务运行中确认弹窗 -->
    <div v-if="showTaskDialog" class="dialog-overlay" @click.self="showTaskDialog = false">
      <div class="dialog-box">
        <div class="dialog-icon">🔄</div>
        <h3 class="dialog-title">有任务正在运行</h3>
        <p class="dialog-message">
          当前正在研究「{{ activeTaskStore.topic }}」，是否查看进度？
        </p>
        <div class="dialog-actions">
          <button class="dialog-btn secondary" @click="showTaskDialog = false">
            取消
          </button>
          <button class="dialog-btn primary" @click="confirmGoToResearch">
            查看进度
          </button>
        </div>
      </div>
    </div>
    
    <!-- 取消任务确认弹窗 -->
    <div v-if="showCancelDialog" class="dialog-overlay" @click.self="showCancelDialog = false">
      <div class="dialog-box">
        <div class="dialog-icon">⚠️</div>
        <h3 class="dialog-title">确认取消任务？</h3>
        <p class="dialog-message">
          取消后当前研究任务将被清除。
        </p>
        <div class="dialog-actions">
          <button class="dialog-btn secondary" @click="showCancelDialog = false">
            返回
          </button>
          <button class="dialog-btn danger" @click="confirmCancelTask">
            确认取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import ShowcaseBackground from '../components/home/ShowcaseBackground.vue'
import { useActiveTaskStore } from '../stores/activeTask'

const router = useRouter()
const activeTaskStore = useActiveTaskStore()
const topic = ref('')
const isLoading = ref(false)
const showTaskDialog = ref(false)
const showCancelDialog = ref(false)
let timer: number | null = null

const hotTags = [
  '咖啡店创业',
  '护肤心得',
  '穿搭分享',
  '美食探店',
  '旅行攻略',
  '健身打卡',
  '家居装修',
  '数码测评'
]

const stageNames: Record<string, string> = {
  planning: '规划中',
  searching: '搜索中',
  analyzing: '分析中',
  generating: '生成中'
}

const getStageName = (stage: string) => stageNames[stage] || stage

const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const selectTag = (tag: string) => {
  topic.value = tag
}

const startResearch = async () => {
  if (!topic.value.trim() || isLoading.value) return
  
  // 如果有进行中的任务，显示确认弹窗
  if (activeTaskStore.hasActiveTask) {
    showTaskDialog.value = true
    return
  }
  
  isLoading.value = true
  
  router.push({
    path: '/research',
    query: { topic: topic.value }
  })
}

const goToResearch = () => {
  router.push('/research')
}

const confirmGoToResearch = () => {
  showTaskDialog.value = false
  router.push('/research')
}

const cancelTask = () => {
  showCancelDialog.value = true
}

const confirmCancelTask = () => {
  showCancelDialog.value = false
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  activeTaskStore.clearTask()
}

// 启动定时器刷新耗时显示
onMounted(() => {
  if (activeTaskStore.hasActiveTask) {
    timer = window.setInterval(() => {
      activeTaskStore.updateTick()
    }, 1000)
  }
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped>
.home-view {
  position: relative;
  z-index: 1;
  max-width: 1000px;
  margin: 0 auto;
  padding-top: 20px;
}

/* Hero Section */
.hero-section {
  text-align: center;
  padding: 50px 60px;
  animation: fadeIn 0.6s ease-out;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(10px);
}

.hero-content {
  margin-bottom: 36px;
}

.brand-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 16px;
  background: rgba(255, 36, 66, 0.08);
  color: var(--primary);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;
  letter-spacing: 0.5px;
  gap: 6px;
}

.platform-slogan {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 20px;
  line-height: 1.6;
}

.search-title {
  font-size: 42px;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 12px;
  letter-spacing: -1px;
}

.search-subtitle {
  font-size: 16px;
  color: var(--text-sub);
  max-width: 500px;
  margin: 0 auto;
}

/* 搜索框 */
.search-box {
  max-width: 650px;
  margin: 0 auto 32px;
  position: relative;
}

.search-input {
  width: 100%;
  padding: 20px 130px 20px 28px;
  background: white;
  border: 2px solid transparent;
  border-radius: 100px;
  font-size: 16px;
  color: var(--text-main);
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.search-input:focus {
  border-color: var(--primary);
  box-shadow: 0 8px 32px rgba(255, 36, 66, 0.12);
  outline: none;
}

.search-input::placeholder {
  color: var(--text-placeholder);
}

.search-btn {
  position: absolute;
  right: 6px;
  top: 6px;
  bottom: 6px;
  padding: 0 28px;
  background: linear-gradient(135deg, var(--primary) 0%, #FF5C72 100%);
  color: white;
  border: none;
  border-radius: 100px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.search-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #FF3B55 0%, #FF7A8C 100%);
  transform: scale(1.02);
}

.search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 热门话题 */
.hot-topics {
  max-width: 600px;
  margin: 0 auto;
}

.topics-title {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

/* 进行中任务入口 */
.active-task-section {
  margin-top: 24px;
  animation: slideUp 0.4s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.active-task-card {
  display: flex;
  align-items: center;
  gap: 20px;
  background: white;
  padding: 20px 28px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid rgba(255, 36, 66, 0.2);
}

.active-task-card:hover {
  border-color: var(--primary);
  box-shadow: 0 8px 32px rgba(255, 36, 66, 0.12);
  transform: translateY(-2px);
}

.task-icon {
  font-size: 32px;
}

.icon-spinning {
  display: inline-block;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.task-info {
  flex: 1;
  text-align: left;
}

.task-status {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.task-topic {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 4px;
}

.task-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.task-stage {
  color: var(--primary);
  font-weight: 500;
}

.task-action, .task-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--primary) 0%, #FF5C72 100%);
  color: white;
  border: none;
  border-radius: 100px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.task-btn:hover {
  transform: scale(1.05);
}

.cancel-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid #e0e0e0;
  background: white;
  color: #999;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.cancel-btn:hover {
  background: #fee;
  border-color: var(--primary);
  color: var(--primary);
}

/* 动画 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 确认弹窗 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.dialog-box {
  background: white;
  border-radius: 20px;
  padding: 32px;
  max-width: 400px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  animation: dialogSlideIn 0.3s ease;
}

@keyframes dialogSlideIn {
  from { 
    opacity: 0; 
    transform: scale(0.9) translateY(20px); 
  }
  to { 
    opacity: 1; 
    transform: scale(1) translateY(0); 
  }
}

.dialog-icon {
  font-size: 48px;
  margin-bottom: 16px;
  animation: spin 2s linear infinite;
}

.dialog-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 12px;
}

.dialog-message {
  font-size: 15px;
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.6;
}

.dialog-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.dialog-btn {
  padding: 12px 28px;
  border-radius: 100px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.dialog-btn.secondary {
  background: #f0f0f0;
  color: var(--text-main);
}

.dialog-btn.secondary:hover {
  background: #e0e0e0;
}

.dialog-btn.primary {
  background: linear-gradient(135deg, var(--primary) 0%, #FF5C72 100%);
  color: white;
}

.dialog-btn.primary:hover {
  transform: scale(1.05);
}
</style>
