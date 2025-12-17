<template>
  <div class="outline-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">编辑大纲</h1>
        <p class="page-subtitle">调整章节顺序，修改内容，打造完美研究报告</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="goBack">
          上一步
        </button>
        <button class="btn btn-primary" @click="generateReport">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          生成报告
        </button>
      </div>
    </div>
    
    <!-- 大纲网格 -->
    <div class="outline-grid">
      <div 
        v-for="(section, index) in store.outline" 
        :key="section.id"
        class="card outline-card"
        :class="{ 'dragging-over': dragOverIndex === index }"
        draggable="true"
        @dragstart="onDragStart($event, index)"
        @dragover.prevent="onDragOver($event, index)"
        @dragleave="onDragLeave"
        @drop="onDrop($event, index)"
      >
        <!-- 顶部栏 -->
        <div class="card-top-bar">
          <div class="page-info">
            <span class="page-number">P{{ index + 1 }}</span>
            <span class="page-type" :class="section.type">{{ getTypeName(section.type) }}</span>
          </div>
          
          <div class="card-controls">
            <div class="drag-handle" title="拖拽排序">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="9" cy="5" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="19" r="1"/>
                <circle cx="15" cy="5" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="19" r="1"/>
              </svg>
            </div>
            <button class="icon-btn" @click="deleteSection(index)" title="删除">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>
        
        <!-- 标题输入 -->
        <input 
          v-model="section.title"
          class="section-title-input"
          placeholder="章节标题..."
          @input="updateSection(section)"
        />
        
        <!-- 内容编辑 -->
        <textarea
          v-model="section.content"
          class="textarea-paper"
          placeholder="在此输入内容..."
          @input="updateSection(section)"
        />
        
        <!-- 图片预览 -->
        <div v-if="section.images && section.images.length > 0" class="image-preview-row">
          <div 
            v-for="(img, imgIdx) in section.images.slice(0, 3)" 
            :key="imgIdx"
            class="image-thumbnail"
          >
            <img :src="img" :alt="`图片 ${imgIdx + 1}`" />
          </div>
          <div v-if="section.images.length > 3" class="image-more">
            +{{ section.images.length - 3 }}
          </div>
        </div>
        
        <div class="word-count">{{ section.content?.length || 0 }} 字</div>
      </div>
      
      <!-- 添加按钮 -->
      <div class="card add-card-dashed" @click="addSection">
        <div class="add-content">
          <div class="add-icon">+</div>
          <span>添加章节</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResearchStore, type OutlineSection } from '../stores/research'

const route = useRoute()
const router = useRouter()
const store = useResearchStore()

const dragOverIndex = ref<number | null>(null)
const draggedIndex = ref<number | null>(null)

const getTypeName = (type: string) => {
  const names: Record<string, string> = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type] || '内容'
}

// 拖拽逻辑
const onDragStart = (e: DragEvent, index: number) => {
  draggedIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
  }
}

const onDragOver = (e: DragEvent, index: number) => {
  if (draggedIndex.value === index) return
  dragOverIndex.value = index
}

const onDragLeave = () => {
  dragOverIndex.value = null
}

const onDrop = (e: DragEvent, index: number) => {
  dragOverIndex.value = null
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    store.moveSection(draggedIndex.value, index)
  }
  draggedIndex.value = null
}

const updateSection = (section: OutlineSection) => {
  store.updateSection(section.id, {
    title: section.title,
    content: section.content
  })
}

const deleteSection = (index: number) => {
  if (confirm('确定要删除这个章节吗？')) {
    const section = store.outline[index]
    if (section) {
      store.deleteSection(section.id)
    }
  }
}

const addSection = () => {
  store.addSection('content', '')
}

const goBack = () => {
  router.push('/research')
}

const generateReport = () => {
  router.push('/report')
}

// 初始化：如果没有大纲数据，创建示例
onMounted(() => {
  if (store.outline.length === 0) {
    // 从路由获取主题或使用默认值
    const topic = route.query.topic as string || store.topic || '研究主题'
    store.setTopic(topic)
    
    // 创建示例大纲
    store.addSection('cover', `# ${topic}\n\n基于小红书笔记的深度研究`)
    store.addSection('content', '## 背景与目的\n\n本研究旨在...')
    store.addSection('content', '## 核心发现\n\n1. 发现一\n2. 发现二\n3. 发现三')
    store.addSection('summary', '## 结论与建议\n\n综合以上分析...')
  }
})
</script>

<style scoped>
.outline-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.header-actions .btn svg {
  margin-right: 6px;
}

/* 网格布局 */
.outline-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
  margin-top: 24px;
}

.outline-card {
  display: flex;
  flex-direction: column;
  padding: 16px;
  min-height: 360px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: all 0.2s ease;
  cursor: default;
}

.outline-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}

.outline-card.dragging-over {
  border: 2px dashed var(--primary);
  opacity: 0.8;
}

/* 顶部栏 */
.card-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f5f5f5;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-number {
  font-size: 14px;
  font-weight: 700;
  color: #ccc;
}

.page-type {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.page-type.cover { color: #FF4D4F; background: #FFF1F0; }
.page-type.content { color: #8c8c8c; background: #f5f5f5; }
.page-type.summary { color: #52C41A; background: #F6FFED; }

.card-controls {
  display: flex;
  gap: 8px;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.outline-card:hover .card-controls {
  opacity: 1;
}

.drag-handle {
  cursor: grab;
  padding: 2px;
  color: #999;
}

.drag-handle:active {
  cursor: grabbing;
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 2px;
  transition: color 0.2s;
}

.icon-btn:hover {
  color: #FF4D4F;
}

/* 标题输入 */
.section-title-input {
  width: 100%;
  border: none;
  background: transparent;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  padding: 0;
  margin-bottom: 12px;
}

.section-title-input:focus {
  outline: none;
}

.section-title-input::placeholder {
  color: #ccc;
}

/* 文本区域 */
.textarea-paper {
  flex: 1;
  width: 100%;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #333;
  resize: none;
  font-family: inherit;
}

.textarea-paper:focus {
  outline: none;
}

/* 图片预览 */
.image-preview-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}

.image-thumbnail {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  overflow: hidden;
}

.image-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-more {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #999;
}

.word-count {
  text-align: right;
  font-size: 11px;
  color: #ddd;
  margin-top: auto;
  padding-top: 8px;
}

/* 添加卡片 */
.add-card-dashed {
  border: 2px dashed #eee;
  background: transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  color: #ccc;
  cursor: pointer;
  transition: all 0.2s;
}

.add-card-dashed:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(255, 36, 66, 0.02);
}

.add-content {
  text-align: center;
}

.add-icon {
  font-size: 32px;
  font-weight: 300;
  margin-bottom: 8px;
}
</style>
