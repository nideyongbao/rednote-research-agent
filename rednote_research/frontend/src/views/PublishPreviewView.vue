<template>
  <div class="publish-preview-view">
    <div class="page-header">
      <div class="header-left">
        <button class="btn btn-ghost" @click="goBack">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="m15 18-6-6 6-6"/>
          </svg>
          返回编辑
        </button>
        <h1 class="page-title">发布预览</h1>
      </div>
      <div class="header-actions">
        <button class="btn btn-primary btn-publish" @click="publish" :disabled="publishing">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2 11 13"/>
            <path d="m22 2-7 20-4-9-9-4 20-7z"/>
          </svg>
          {{ publishing ? '发布中...' : '发布到小红书' }}
        </button>
      </div>
    </div>

    <div class="preview-container">
      <!-- 手机预览框架 -->
      <div class="phone-frame">
        <div class="phone-notch"></div>
        <div class="phone-screen">
          <!-- 图片轮播区域 -->
          <div class="image-carousel">
            <div class="carousel-track" :style="{ transform: `translateX(-${currentImageIndex * 100}%)` }">
              <div 
                v-for="(img, index) in allImages" 
                :key="index"
                class="carousel-slide"
              >
                <img :src="getImageUrl(img)" :alt="`图片 ${index + 1}`" />
              </div>
            </div>
            
            <!-- 轮播指示器 -->
            <div class="carousel-dots">
              <span 
                v-for="(_, index) in allImages" 
                :key="index"
                class="dot"
                :class="{ active: currentImageIndex === index }"
                @click="currentImageIndex = index"
              ></span>
            </div>
            
            <!-- 轮播箭头 -->
            <button 
              v-if="allImages.length > 1"
              class="carousel-arrow prev" 
              @click="prevImage"
              :disabled="currentImageIndex === 0"
            >‹</button>
            <button 
              v-if="allImages.length > 1"
              class="carousel-arrow next" 
              @click="nextImage"
              :disabled="currentImageIndex === allImages.length - 1"
            >›</button>
          </div>

          <!-- 内容区域 -->
          <div class="content-area">
            <h2 class="note-title">{{ draft.title }}</h2>
            <p class="note-content">{{ draft.content }}</p>
            
            <div class="note-tags">
              <span v-for="tag in draft.tags" :key="tag" class="note-tag">
                #{{ tag }}
              </span>
            </div>

            <!-- 模拟互动区 -->
            <div class="note-actions">
              <div class="action-item">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
                <span>赞</span>
              </div>
              <div class="action-item">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>
                </svg>
                <span>收藏</span>
              </div>
              <div class="action-item">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <span>评论</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧信息 -->
      <div class="preview-info">
        <div class="info-card">
          <h3>📋 发布信息</h3>
          <div class="info-item">
            <span class="label">标题</span>
            <span class="value">{{ draft.title }}</span>
          </div>
          <div class="info-item">
            <span class="label">正文字数</span>
            <span class="value">{{ draft.content.length }} 字</span>
          </div>
          <div class="info-item">
            <span class="label">图片数量</span>
            <span class="value">{{ allImages.length }} 张</span>
          </div>
          <div class="info-item">
            <span class="label">标签</span>
            <span class="value">{{ draft.tags.length }} 个</span>
          </div>
        </div>

        <div class="info-card tips">
          <h3>💡 发布提示</h3>
          <ul>
            <li>发布后笔记将公开可见</li>
            <li>优质内容更容易获得推荐</li>
            <li>封面图很重要，影响点击率</li>
            <li>适当的标签有助于曝光</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const draft = ref({
  id: '',
  topic: '',
  title: '',
  content: '',
  cover_image: '',
  section_images: [] as string[],
  tags: [] as string[],
  status: 'draft'
})

const publishing = ref(false)
const currentImageIndex = ref(0)

// 所有图片
const allImages = computed(() => {
  const images: string[] = []
  if (draft.value.cover_image) {
    images.push(draft.value.cover_image)
  }
  images.push(...draft.value.section_images)
  return images
})

// 生命周期
onMounted(async () => {
  const draftId = route.params.draftId as string
  if (draftId) {
    await loadDraft(draftId)
  } else {
    router.push('/report')
  }
})

// 加载草稿
async function loadDraft(draftId: string) {
  try {
    const response = await fetch(`/api/publish/${draftId}`)
    const result = await response.json()
    
    if (result.success) {
      draft.value = result.data
    } else {
      alert('加载草稿失败')
      router.push('/report')
    }
  } catch (error) {
    console.error('Load draft error:', error)
    router.push('/report')
  }
}

// 图片 URL 处理
function getImageUrl(path: string) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  const filename = path.split('/').pop() || path.split('\\').pop()
  return `/api/publish/${draft.value.id}/images/${filename}`
}

// 轮播控制
function prevImage() {
  if (currentImageIndex.value > 0) {
    currentImageIndex.value--
  }
}

function nextImage() {
  if (currentImageIndex.value < allImages.value.length - 1) {
    currentImageIndex.value++
  }
}

// 发布
async function publish() {
  if (publishing.value) return
  
  publishing.value = true
  
  // 跳转到结果页，让结果页处理发布
  router.push({ 
    name: 'publish-result', 
    params: { draftId: draft.value.id } 
  })
}

// 导航
function goBack() {
  router.push({ 
    name: 'publish-edit', 
    params: { draftId: draft.value.id } 
  })
}
</script>

<style scoped>
.publish-preview-view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 20px 40px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid #eee;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn-publish {
  padding: 12px 24px;
}

.preview-container {
  display: flex;
  gap: 40px;
  justify-content: center;
}

/* 手机框架 */
.phone-frame {
  width: 340px;
  background: #1a1a1a;
  border-radius: 40px;
  padding: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.phone-notch {
  width: 120px;
  height: 28px;
  background: #1a1a1a;
  border-radius: 14px;
  margin: 0 auto 8px;
}

.phone-screen {
  background: white;
  border-radius: 32px;
  overflow: hidden;
  height: 600px;
  display: flex;
  flex-direction: column;
}

/* 图片轮播 */
.image-carousel {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: #f5f5f5;
}

.carousel-track {
  display: flex;
  height: 100%;
  transition: transform 0.3s ease;
}

.carousel-slide {
  min-width: 100%;
  height: 100%;
}

.carousel-slide img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.carousel-dots {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 6px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s;
}

.dot.active {
  width: 18px;
  border-radius: 3px;
  background: white;
}

.carousel-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.3);
  color: white;
  border: none;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.carousel-arrow:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.5);
}

.carousel-arrow:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.carousel-arrow.prev {
  left: 12px;
}

.carousel-arrow.next {
  right: 12px;
}

/* 内容区 */
.content-area {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.note-title {
  font-size: 17px;
  font-weight: 600;
  color: #222;
  margin: 0 0 12px 0;
  line-height: 1.4;
}

.note-content {
  font-size: 14px;
  color: #444;
  line-height: 1.7;
  margin: 0 0 16px 0;
  white-space: pre-wrap;
}

.note-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.note-tag {
  font-size: 13px;
  color: #4a90e2;
}

.note-actions {
  display: flex;
  justify-content: space-around;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #666;
}

.action-item span {
  font-size: 12px;
}

/* 右侧信息 */
.preview-info {
  width: 280px;
}

.info-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 20px;
}

.info-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: var(--text-main);
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  color: #999;
  font-size: 14px;
}

.info-item .value {
  color: var(--text-main);
  font-size: 14px;
  font-weight: 500;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  font-size: 13px;
  color: #666;
  margin: 8px 0;
  line-height: 1.5;
}

/* 按钮样式 */
.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #e6203a;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: #f5f5f5;
}

/* 响应式 */
@media (max-width: 768px) {
  .preview-container {
    flex-direction: column;
    align-items: center;
  }
  
  .preview-info {
    width: 100%;
    max-width: 340px;
  }
}
</style>
