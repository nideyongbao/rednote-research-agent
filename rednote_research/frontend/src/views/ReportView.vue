<template>
  <div class="report-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">研究报告</h1>
        <p class="page-subtitle">{{ store.topic || '研究主题' }}</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="goBack">
          返回编辑
        </button>
        <button class="btn btn-primary" @click="exportReport">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导出 HTML
        </button>
      </div>
    </div>
    
    <div class="report-layout">
      <!-- 左侧目录 -->
      <aside class="report-toc">
        <div class="toc-header">目录</div>
        <nav class="toc-nav">
          <a 
            v-for="(section, index) in store.outline" 
            :key="section.id"
            :href="`#section-${section.id}`"
            class="toc-item"
            :class="{ active: activeSection === section.id }"
            @click.prevent="scrollToSection(section.id)"
          >
            <span class="toc-number">{{ index + 1 }}</span>
            <span class="toc-title">{{ section.title || `章节 ${index + 1}` }}</span>
          </a>
        </nav>
        
        <!-- 统计摘要 -->
        <div class="toc-stats">
          <div class="stat-item">
            <span class="stat-value">{{ store.outline.length }}</span>
            <span class="stat-label">章节</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ totalWords }}</span>
            <span class="stat-label">字数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ totalImages }}</span>
            <span class="stat-label">图片</span>
          </div>
        </div>
      </aside>
      
      <!-- 右侧报告内容 -->
      <main class="report-content">
        <!-- 关键发现仪表盘 -->
        <div v-if="store.keyFindings.length > 0" class="card dashboard-card">
          <h2 class="dashboard-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
            </svg>
            关键发现
          </h2>
          <div class="findings-grid">
            <div 
              v-for="(finding, index) in store.keyFindings" 
              :key="index"
              class="finding-card"
            >
              <span class="finding-number">{{ index + 1 }}</span>
              <p class="finding-text">{{ finding }}</p>
            </div>
          </div>
        </div>
        
        <!-- 报告摘要 -->
        <div v-if="store.summary" class="card summary-card">
          <h2 class="section-title">📋 研究摘要</h2>
          <p class="summary-text">{{ store.summary }}</p>
        </div>
        
        <!-- 章节内容 -->
        <div 
          v-for="(section, index) in store.outline" 
          :key="section.id"
          :id="`section-${section.id}`"
          class="card section-card"
        >
          <div class="section-header">
            <span class="section-number">{{ index + 1 }}</span>
            <div class="section-meta">
              <span class="section-type" :class="section.type">{{ getTypeName(section.type) }}</span>
            </div>
          </div>
          
          <h2 class="section-title">{{ section.title || `章节 ${index + 1}` }}</h2>
          
          <div class="section-content" v-html="formatContent(section.content)"></div>
          
          <!-- 图片展示 -->
          <div v-if="section.images && section.images.length > 0" class="section-images">
            <div 
              v-for="(img, imgIdx) in section.images" 
              :key="imgIdx"
              class="section-image"
            >
              <img :src="img" :alt="`图片 ${imgIdx + 1}`" @click="viewImage(img)" />
            </div>
          </div>
        </div>
        
        <!-- 数据来源 -->
        <div v-if="store.notes.length > 0" class="card sources-card">
          <h2 class="section-title">📚 数据来源</h2>
          <p class="sources-desc">本研究基于 {{ store.notes.length }} 篇小红书笔记进行分析</p>
          <div class="sources-list">
            <div 
              v-for="note in store.notes.slice(0, 5)" 
              :key="note.id"
              class="source-item"
            >
              <div class="source-title">{{ note.title }}</div>
              <div class="source-meta">
                <span>{{ note.author }}</span>
                <span>❤️ {{ note.likes }}</span>
              </div>
            </div>
          </div>
          <div v-if="store.notes.length > 5" class="sources-more">
            还有 {{ store.notes.length - 5 }} 篇笔记未显示
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useResearchStore } from '../stores/research'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const router = useRouter()
const store = useResearchStore()

const activeSection = ref('')

const getTypeName = (type: string) => {
  const names: Record<string, string> = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type] || '内容'
}

// 计算统计数据
const totalWords = computed(() => {
  return store.outline.reduce((sum, section) => sum + (section.content?.length || 0), 0)
})

const totalImages = computed(() => {
  return store.outline.reduce((sum, section) => sum + (section.images?.length || 0), 0)
})

// 配置 marked 选项
marked.setOptions({
  breaks: true,        // 支持 GFM 换行
  gfm: true,           // 启用 GitHub Flavored Markdown
})

// 格式化内容（使用 marked 库进行标准 Markdown 渲染）
const formatContent = (content: string) => {
  if (!content) return ''
  // 使用 marked 解析 markdown，DOMPurify 过滤 XSS
  const html = marked.parse(content) as string
  return DOMPurify.sanitize(html)
}

// 滚动到章节
const scrollToSection = (id: string) => {
  const el = document.getElementById(`section-${id}`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeSection.value = id
  }
}

// 查看大图
const viewImage = (url: string) => {
  window.open(url, '_blank')
}

// 导出报告
const exportReport = () => {
  const report = store.getReport
  const html = generateReportHTML(report)
  
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `research_report_${Date.now()}.html`
  a.click()
  URL.revokeObjectURL(url)
}

const generateReportHTML = (report: any) => {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${report.topic} - 研究报告</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; color: #333; }
    h1 { color: #ff2442; }
    .section { margin: 40px 0; padding: 20px; background: #f9f9f9; border-radius: 12px; }
    .finding { background: white; padding: 12px 16px; margin: 8px 0; border-radius: 8px; border-left: 3px solid #ff2442; }
  </style>
</head>
<body>
  <h1>${report.topic}</h1>
  <p><strong>生成时间：</strong>${new Date(report.createdAt).toLocaleString('zh-CN')}</p>
  
  ${report.summary ? `<div class="section"><h2>研究摘要</h2><p>${report.summary}</p></div>` : ''}
  
  ${report.keyFindings.length > 0 ? `
    <div class="section">
      <h2>关键发现</h2>
      ${report.keyFindings.map((f: string, i: number) => `<div class="finding">${i + 1}. ${f}</div>`).join('')}
    </div>
  ` : ''}
  
  ${report.sections.map((section: any, i: number) => `
    <div class="section">
      <h2>${i + 1}. ${section.title || `章节 ${i + 1}`}</h2>
      <p>${section.content?.replace(/\n/g, '<br>') || ''}</p>
    </div>
  `).join('')}
  
  <footer style="text-align: center; color: #999; margin-top: 60px; padding-top: 20px; border-top: 1px solid #eee;">
    由 RedNote Research Agent 生成
  </footer>
</body>
</html>`
}

const goBack = () => {
  router.push('/outline')
}

// 监听滚动更新当前章节
let scrollHandler: (() => void) | null = null

onMounted(() => {
  // 如果没有数据，创建示例
  if (store.outline.length === 0) {
    store.addSection('cover', '# 示例研究报告\n\n研究主题概述')
    store.addSection('content', '## 研究发现\n\n1. 发现一\n2. 发现二')
    store.addSection('summary', '## 总结\n\n研究结论...')
    store.setKeyFindings(['用户对产品质量非常关注', '价格敏感度较高', '口碑推荐影响大'])
    store.setSummary('本研究通过分析小红书平台上的相关笔记，发现用户最关心产品质量和性价比...')
  }
  
  if (store.outline.length > 0) {
    activeSection.value = store.outline[0].id
  }
  
  scrollHandler = () => {
    const sections = store.outline.map(s => document.getElementById(`section-${s.id}`))
    for (let i = sections.length - 1; i >= 0; i--) {
      const el = sections[i]
      if (el && el.getBoundingClientRect().top <= 100) {
        activeSection.value = store.outline[i].id
        break
      }
    }
  }
  
  window.addEventListener('scroll', scrollHandler)
})

onUnmounted(() => {
  if (scrollHandler) {
    window.removeEventListener('scroll', scrollHandler)
  }
})
</script>

<style scoped>
.report-view {
  max-width: 1200px;
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

/* 布局 */
.report-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 32px;
  margin-top: 24px;
}

/* 目录 */
.report-toc {
  position: sticky;
  top: 20px;
  height: fit-content;
}

.toc-header {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.toc-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  text-decoration: none;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.toc-item:hover {
  background: #f5f5f5;
  color: var(--text-main);
}

.toc-item.active {
  background: rgba(255, 36, 66, 0.08);
  color: var(--primary);
}

.toc-number {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.toc-item.active .toc-number {
  background: var(--primary);
  color: white;
}

.toc-title {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toc-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #eee;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary);
}

/* 报告内容 */
.report-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 仪表盘 */
.dashboard-card {
  background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
  border: 1px solid rgba(255, 36, 66, 0.1);
}

.dashboard-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  color: var(--primary);
  margin-bottom: 20px;
}

.findings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.finding-card {
  background: white;
  padding: 16px;
  border-radius: 10px;
  display: flex;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.finding-number {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.finding-text {
  font-size: 14px;
  color: var(--text-main);
  margin: 0;
  line-height: 1.5;
}

/* 摘要卡片 */
.summary-card .section-title {
  margin-bottom: 12px;
}

.summary-text {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.7;
}

/* 章节卡片 */
.section-card {
  scroll-margin-top: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-number {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: #999;
}

.section-type {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.section-type.cover { color: #FF4D4F; background: #FFF1F0; }
.section-type.content { color: #8c8c8c; background: #f5f5f5; }
.section-type.summary { color: #52C41A; background: #F6FFED; }

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 16px;
}

.section-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.section-content :deep(h2),
.section-content :deep(h3),
.section-content :deep(h4) {
  color: var(--text-main);
  margin: 16px 0 8px;
}

.section-content :deep(li) {
  margin: 4px 0;
}

.section-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.section-image {
  aspect-ratio: 4/3;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.section-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.section-image:hover img {
  transform: scale(1.05);
}

/* 数据来源 */
.sources-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-item {
  padding: 12px 16px;
  background: #f9f9f9;
  border-radius: 8px;
}

.source-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.source-meta {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  gap: 12px;
}

.sources-more {
  text-align: center;
  font-size: 13px;
  color: var(--text-secondary);
  padding-top: 12px;
}

/* 响应式 */
@media (max-width: 768px) {
  .report-layout {
    grid-template-columns: 1fr;
  }
  
  .report-toc {
    position: static;
    display: none;
  }
}
</style>
