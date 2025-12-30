<template>
  <div class="publish-edit-view">
    <!-- Lightbox 图片查看器 -->
    <Teleport to="body">
      <div v-if="lightboxVisible" class="lightbox-overlay" @click="closeLightbox">
        <button class="lightbox-close" @click="closeLightbox">×</button>
        <img 
          :src="lightboxImage" 
          class="lightbox-image" 
          referrerpolicy="no-referrer"
          @click.stop
        />
        <div v-if="lightboxImages.length > 1" class="lightbox-nav">
          <button @click.stop="prevImage" :disabled="lightboxIndex <= 0">‹</button>
          <span>{{ lightboxIndex + 1 }} / {{ lightboxImages.length }}</span>
          <button @click.stop="nextImage" :disabled="lightboxIndex >= lightboxImages.length - 1">›</button>
        </div>
      </div>
    </Teleport>
    <div class="page-header">
      <div class="header-left">
        <button class="btn btn-ghost" @click="goBack">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="m15 18-6-6 6-6"/>
          </svg>
          返回
        </button>
        <h1 class="page-title">发布到小红书</h1>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="saveDraft" :disabled="saving">
          {{ saving ? '保存中...' : '保存草稿' }}
        </button>
        <button class="btn btn-primary" @click="goToPreview" :disabled="!canPreview">
          预览
        </button>
      </div>
    </div>

    <div class="edit-container">
      <!-- 左侧：内容编辑 -->
      <div class="edit-section">
        <div class="card">
          <h3 class="section-title">📝 标题</h3>
          <div class="input-wrapper">
            <input 
              type="text" 
              v-model="draft.title" 
              placeholder="输入标题（建议15字以内）"
              maxlength="20"
              class="title-input"
            />
            <span class="char-count" :class="{ over: draft.title.length > 18 }">
              {{ draft.title.length }}/20
            </span>
          </div>
        </div>

        <div class="card">
          <h3 class="section-title">📄 正文</h3>
          <div class="textarea-wrapper">
            <textarea 
              v-model="draft.content" 
              placeholder="输入正文内容（图文笔记以图为主，文字简短精炼）"
              maxlength="200"
              class="content-textarea"
              rows="6"
            ></textarea>
            <span class="char-count" :class="{ over: draft.content.length > 180 }">
              {{ draft.content.length }}/200
            </span>
          </div>
        </div>

        <div class="card">
          <h3 class="section-title">🏷️ 标签 <span class="tag-count">{{ draft.tags.length }}/8</span></h3>
          <div class="tags-editor">
            <div class="tags-list">
              <span 
                v-for="(tag, index) in draft.tags" 
                :key="index" 
                class="tag"
              >
                #{{ tag }}
                <button class="tag-remove" @click="removeTag(index)">×</button>
              </span>
              <div class="tag-input-wrapper" v-if="draft.tags.length < 8">
                <input 
                  type="text" 
                  v-model="newTag" 
                  placeholder="添加标签"
                  @keydown.enter.prevent="addTag"
                  @keydown.space.prevent="addTag"
                  class="tag-input"
                />
                <button class="btn btn-add-tag" @click="addTag" type="button">+</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：图片管理 -->
      <div class="images-section">
        <div class="card">
          <div class="section-header">
            <h3 class="section-title">📸 图片</h3>
            <div class="image-actions">
              <button 
                class="btn btn-secondary btn-sm" 
                @click="generateCoverImage"
                :disabled="generating"
              >
                {{ generating ? '生成中...' : '生成封面图' }}
              </button>
              <button 
                class="btn btn-secondary btn-sm" 
                @click="generateSectionImages"
                :disabled="generating"
              >
                生成内容图
              </button>
            </div>
          </div>

          <!-- 生成进度 -->
          <div v-if="generatingLogs.length > 0" class="generate-logs">
            <div 
              v-for="(log, index) in generatingLogs" 
              :key="index" 
              class="log-item"
            >
              {{ log }}
            </div>
          </div>

          <!-- 图片列表 -->
          <div class="images-grid">
            <!-- 封面图 -->
            <div 
              class="image-item cover-image"
              :class="{ empty: !draft.cover_image }"
            >
              <div v-if="draft.cover_image" class="image-content">
                <img :src="getImageUrl(draft.cover_image)" alt="封面图" @click="viewImage(getImageUrl(draft.cover_image))" class="clickable-image" />
                <div class="image-overlay">
                  <span class="image-label">封面</span>
                  <button class="btn-icon" @click="removeCoverImage">×</button>
                </div>
              </div>
              <div v-else class="image-placeholder">
                <span>封面图</span>
                <small>点击"生成封面图"</small>
              </div>
            </div>

            <!-- 章节图 -->
            <div 
              v-for="(img, index) in draft.section_images" 
              :key="index"
              class="image-item"
            >
              <div class="image-content">
                <img :src="getImageUrl(img)" :alt="`内容图 ${index + 1}`" @click="viewImage(getImageUrl(img))" class="clickable-image" />
                <div class="image-overlay">
                  <span class="image-label">{{ index + 1 }}</span>
                  <button class="btn-icon" @click="removeSectionImage(index)">×</button>
                </div>
              </div>
            </div>

            <!-- 添加更多占位 -->
            <div 
              v-if="totalImages < 9" 
              class="image-item empty add-more"
              @click="generateSectionImages"
            >
              <div class="image-placeholder">
                <span>+</span>
                <small>添加图片</small>
              </div>
            </div>
          </div>

          <p class="images-tip">
            💡 小红书图文笔记建议 3-9 张图片，当前 {{ totalImages }} 张
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useResearchStore } from '../stores/research'

const router = useRouter()
const route = useRoute()
const store = useResearchStore()

// 草稿数据
const draft = ref({
  id: '',
  topic: '',
  title: '',
  content: '',
  cover_image: '',
  section_images: [] as string[],
  tags: [] as string[],
  status: 'draft',
  key_findings: [] as string[],
  sections: [] as any[]
})

const newTag = ref('')
const saving = ref(false)
const generating = ref(false)
const generatingLogs = ref<string[]>([])

// Lightbox 状态
const lightboxVisible = ref(false)
const lightboxImage = ref('')
const lightboxImages = ref<string[]>([])
const lightboxIndex = ref(0)

// 计算属性
const totalImages = computed(() => {
  return (draft.value.cover_image ? 1 : 0) + draft.value.section_images.length
})

const canPreview = computed(() => {
  return draft.value.title.trim() && totalImages.value >= 1
})

// 生命周期
onMounted(async () => {
  const draftId = route.params.draftId as string
  
  if (draftId) {
    if (store.currentDraftId !== draftId) {
      store.setDraftId(draftId)
    }
    // 加载已有草稿
    await loadDraft(draftId)
  } else {
    // 从 store 创建新草稿
    await createDraft()
  }
  
  isInitialized.value = true
  
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
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
    alert('加载草稿失败')
    router.push('/report')
  }
}

// 创建新草稿
async function createDraft() {
  // 检查是否有关联的研究数据
  if (!store.topic && !store.id) {
    alert('未找到关联的研究数据，请先选择一份研究报告')
    router.push('/history')
    return
  }

  try {
    const response = await fetch('/api/publish/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: store.topic,
        summary: store.summary,
        key_findings: store.keyFindings,
        sections: store.outline,
        notes: store.notes,
        source_id: store.id // 关联原始研究记录
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      draft.value = result.data
      store.setDraftId(result.data.id)
      isInitialized.value = true
      // 更新 URL
      router.replace({ params: { draftId: result.data.id } })
    } else {
      alert('创建草稿失败: ' + (result.message || '未知错误'))
    }
  } catch (error) {
    console.error('Create draft error:', error)
    alert('创建草稿失败')
  }
}

// 保存草稿
async function saveDraft(silent = false) {
  if (!draft.value.id) return
  
  saving.value = true
  
  try {
    const response = await fetch(`/api/publish/${draft.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: draft.value.title,
        content: draft.value.content,
        tags: draft.value.tags,
        cover_image: draft.value.cover_image,
        section_images: draft.value.section_images
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      draft.value = result.data
      if (!silent) alert('保存成功！')
    }
  } catch (error) {
    console.error('Save draft error:', error)
    if (!silent) alert('保存失败')
  } finally {
    saving.value = false
  }
}

// 自动保存
let autoSaveTimer: any = null
const isInitialized = ref(false)

watch(
  () => [draft.value.title, draft.value.content, draft.value.tags],
  (newVal, oldVal) => {
    // 首次加载不触发
    if (!isInitialized.value) return
    
    // 避免保存后的回显触发自动保存
    if (saving.value) return
    
    // 简单比较是否真的有变动
    if (JSON.stringify(newVal) === JSON.stringify(oldVal)) return

    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => {
      if (draft.value.id && !saving.value) saveDraft(true)
    }, 2000)
  },
  { deep: true }
)

// 生成图片通用方法
async function generateImages(type: 'cover' | 'section') {
  if (!draft.value.id) return
  
  generating.value = true
  generatingLogs.value = []
  
  try {
    const eventSource = new EventSource(`/api/publish/${draft.value.id}/generate-images?type=${type}`)
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'log') {
        generatingLogs.value.push(data.message)
      } else if (data.type === 'complete') {
        draft.value = data.data
        eventSource.close()
        generating.value = false
      } else if (data.type === 'error') {
        alert('生成失败: ' + data.message)
        eventSource.close()
        generating.value = false
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
      generating.value = false
    }
  } catch (error) {
    console.error('Generate images error:', error)
    generating.value = false
  }
}

// 生成封面图
function generateCoverImage() {
  generateImages('cover')
}

// 生成章节图
function generateSectionImages() {
  generateImages('section')
}

// 标签管理
function addTag() {
  const tag = newTag.value.trim().replace(/^#/, '')
  if (tag && !draft.value.tags.includes(tag) && draft.value.tags.length < 8) {
    draft.value.tags.push(tag)
    newTag.value = ''
  }
}

function removeTag(index: number) {
  draft.value.tags.splice(index, 1)
}

// 图片管理
function getImageUrl(path: string) {
  if (!path) return ''
  if (path.startsWith('http')) return path
  // 本地图片通过 API 访问
  const filename = path.split('/').pop() || path.split('\\').pop()
  return `/api/publish/${draft.value.id}/images/${filename}`
}

function removeCoverImage() {
  draft.value.cover_image = ''
  saveDraft()
}

function removeSectionImage(index: number) {
  draft.value.section_images.splice(index, 1)
  saveDraft()
}

// 导航
function goBack() {
  router.push('/report')
}

function goToPreview() {
  if (canPreview.value) {
    saveDraft()
    router.push({ name: 'publish-preview', params: { draftId: draft.value.id } })
  }
}

// Lightbox 逻辑
const viewImage = (url: string) => {
  const images: string[] = []
  if (draft.value.cover_image) images.push(getImageUrl(draft.value.cover_image))
  draft.value.section_images.forEach(img => images.push(getImageUrl(img)))
  
  lightboxImages.value = images
  lightboxIndex.value = images.indexOf(url)
  if (lightboxIndex.value === -1) lightboxIndex.value = 0
  
  lightboxImage.value = url
  lightboxVisible.value = true
}

const closeLightbox = () => {
  lightboxVisible.value = false
}

const prevImage = () => {
  if (lightboxIndex.value > 0) {
    lightboxIndex.value--
    lightboxImage.value = lightboxImages.value[lightboxIndex.value]
  }
}

const nextImage = () => {
  if (lightboxIndex.value < lightboxImages.value.length - 1) {
    lightboxIndex.value++
    lightboxImage.value = lightboxImages.value[lightboxIndex.value]
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  if (!lightboxVisible.value) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowLeft') prevImage()
  if (e.key === 'ArrowRight') nextImage()
}
</script>

<style scoped>
.publish-edit-view {
  max-width: 1200px;
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

.edit-container {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 24px;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 16px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header .section-title {
  margin: 0;
}

.image-actions {
  display: flex;
  gap: 8px;
}

/* 输入框样式 */
.input-wrapper,
.textarea-wrapper {
  position: relative;
}

.title-input {
  width: 100%;
  padding: 12px 60px 12px 16px;
  border: 2px solid #eee;
  border-radius: 10px;
  font-size: 16px;
  transition: border-color 0.2s;
}

.title-input:focus {
  outline: none;
  border-color: var(--primary);
}

.content-textarea {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #eee;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  min-height: 120px;
  transition: border-color 0.2s;
}

.content-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.char-count {
  position: absolute;
  right: 12px;
  bottom: 12px;
  font-size: 12px;
  color: #999;
}

.char-count.over {
  color: var(--primary);
}

/* 标签编辑器 */
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(255, 36, 66, 0.08);
  color: var(--primary);
  border-radius: 20px;
  font-size: 13px;
}

.tag-remove {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  padding: 0 2px;
  font-size: 16px;
  line-height: 1;
}

.tag-input-wrapper {
  display: flex;
  gap: 4px;
}

.tag-input {
  width: 100px;
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 20px;
  font-size: 13px;
}

.tag-input:focus {
  outline: none;
  border-color: var(--primary);
}

.tag-count {
  font-size: 12px;
  color: #999;
  font-weight: normal;
  margin-left: 8px;
}

.btn-add-tag {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary);
  color: white;
  border: none;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-add-tag:hover {
  background: #e6203a;
  transform: scale(1.1);
}

/* 图片区域 */
.generate-logs {
  background: #f9f9f9;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  max-height: 150px;
  overflow-y: auto;
  font-size: 13px;
}

.log-item {
  padding: 4px 0;
  color: #666;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.image-item {
  aspect-ratio: 3/4;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}

.image-item.empty {
  border: 2px dashed #ddd;
  background: #f9f9f9;
}

.image-item.cover-image {
  grid-column: span 1;
}

.image-content {
  width: 100%;
  height: 100%;
  position: relative;
}

.image-content img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 50%);
  display: flex;
  justify-content: space-between;
  padding: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-item:hover .image-overlay {
  opacity: 1;
}

.image-label {
  background: var(--primary);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.btn-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(0,0,0,0.5);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
  gap: 4px;
}

.image-placeholder span {
  font-size: 24px;
}

.image-placeholder small {
  font-size: 11px;
}

.add-more {
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.add-more:hover {
  border-color: var(--primary);
  background: rgba(255, 36, 66, 0.04);
}

.images-tip {
  margin-top: 16px;
  font-size: 13px;
  color: #999;
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

.btn-secondary {
  background: #f5f5f5;
  color: var(--text-main);
}

.btn-secondary:hover:not(:disabled) {
  background: #eee;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: #f5f5f5;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

/* 响应式 */
@media (max-width: 900px) {
  .edit-container {
    grid-template-columns: 1fr;
  }
  
  .images-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}


/* Lightbox 样式 */
.clickable-image {
  cursor: zoom-in;
}

.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.lightbox-image {
  max-width: 90vw;
  max-height: 80vh;
  object-fit: contain;
  box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

.lightbox-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: none;
  border: none;
  color: white;
  font-size: 32px;
  cursor: pointer;
  z-index: 10000;
}

.lightbox-nav {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  color: white;
}

.lightbox-nav button {
  background: rgba(255,255,255,0.2);
  border: none;
  color: white;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.lightbox-nav button:hover:not(:disabled) {
  background: rgba(255,255,255,0.3);
}

.lightbox-nav button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
