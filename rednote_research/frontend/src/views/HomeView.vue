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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ShowcaseBackground from '../components/home/ShowcaseBackground.vue'

const router = useRouter()
const topic = ref('')
const isLoading = ref(false)

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

const selectTag = (tag: string) => {
  topic.value = tag
}

const startResearch = async () => {
  if (!topic.value.trim() || isLoading.value) return
  
  isLoading.value = true
  
  router.push({
    path: '/research',
    query: { topic: topic.value }
  })
}
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

/* 动画 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
