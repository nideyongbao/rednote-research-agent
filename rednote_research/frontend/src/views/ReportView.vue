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
        <div class="export-dropdown">
          <button class="btn btn-primary" @click="toggleExportMenu">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            导出
            <svg class="dropdown-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          <div v-if="showExportMenu" class="export-menu">
            <button @click="exportReport('html')">📄 HTML</button>
            <button @click="exportReport('markdown')">📝 Markdown</button>
            <button @click="exportReport('pdf')">📕 PDF</button>
          </div>
        </div>
        <button class="btn btn-xiaohongshu" @click="goToPublish">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2 11 13"/>
            <path d="m22 2-7 20-4-9-9-4 20-7z"/>
          </svg>
          发布到小红书
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
              <img 
                :src="img" 
                :alt="`图片 ${imgIdx + 1}`" 
                referrerpolicy="no-referrer"
                loading="lazy"
                @click="viewImage(img)"
                @error="handleImageError($event)" 
              />
            </div>
          </div>
        </div>
        
        <!-- 数据来源 -->
        <div v-if="store.notes.length > 0" class="card sources-card">
          <h2 class="section-title">📚 数据来源</h2>
          <p class="sources-desc">本研究基于 {{ store.notes.length }} 篇小红书笔记进行分析</p>
          <div class="sources-list">
            <div 
              v-for="note in store.notes" 
              :key="note.id"
              class="source-item"
            >
              <a 
                :href="note.url" 
                target="_blank" 
                rel="noopener noreferrer"
                class="source-title source-link"
              >
                {{ note.title }}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
              </a>
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
const showExportMenu = ref(false)

const toggleExportMenu = () => {
  showExportMenu.value = !showExportMenu.value
}

// 点击外部关闭菜单
const closeExportMenu = (e: Event) => {
  const target = e.target as HTMLElement
  if (!target.closest('.export-dropdown')) {
    showExportMenu.value = false
  }
}

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

// Lightbox 图片查看器状态
const lightboxVisible = ref(false)
const lightboxImage = ref('')
const lightboxImages = ref<string[]>([])
const lightboxIndex = ref(0)

// 查看大图（使用 Lightbox）
const viewImage = (url: string) => {
  // 收集所有图片
  const allImages: string[] = []
  store.outline.forEach(section => {
    if (section.images) {
      allImages.push(...section.images)
    }
  })
  
  lightboxImages.value = allImages
  lightboxIndex.value = allImages.indexOf(url)
  if (lightboxIndex.value === -1) lightboxIndex.value = 0
  lightboxImage.value = url
  lightboxVisible.value = true
  
  // 禁止背景滚动
  document.body.style.overflow = 'hidden'
}

const closeLightbox = () => {
  lightboxVisible.value = false
  document.body.style.overflow = ''
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

// 键盘导航
const handleKeydown = (e: KeyboardEvent) => {
  if (!lightboxVisible.value) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowLeft') prevImage()
  if (e.key === 'ArrowRight') nextImage()
}

// 图片加载失败处理
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  if (img) {
    img.style.display = 'none'
  }
}

// 导出报告
const exportReport = async (format: 'html' | 'markdown' | 'pdf') => {
  showExportMenu.value = false
  
  if (format === 'html') {
    // HTML导出使用前端逻辑
    const report = store.getReport
    const html = generateReportHTML(report)
    
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `research_report_${Date.now()}.html`
    a.click()
    URL.revokeObjectURL(url)
  } else {
    // Markdown/PDF调用后端API
    try {
      const response = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format,
          topic: store.topic,
          insights: store.getReport.insights || {},
          outline: store.outline,
          notes: store.notes
        })
      })
      
      if (!response.ok) {
        const error = await response.json()
        alert(error.detail || '导出失败')
        return
      }
      
      // 下载文件
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `research_report_${Date.now()}.${format === 'markdown' ? 'md' : 'pdf'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('导出失败，请重试')
    }
  }
}

const generateReportHTML = (report: any) => {
  // 使用 marked 解析 markdown 内容
  const renderMarkdown = (content: string) => {
    if (!content) return ''
    return marked.parse(content) as string
  }
  
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${report.topic} - 研究报告</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
      max-width: 900px; 
      margin: 0 auto; 
      padding: 40px 20px; 
      color: #333;
      line-height: 1.8;
      background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
    }
    h1 { color: #ff2442; font-size: 28px; margin-bottom: 16px; }
    h2 { color: #333; font-size: 22px; margin: 24px 0 16px; border-bottom: 2px solid #ff2442; padding-bottom: 8px; }
    h3 { color: #555; font-size: 18px; margin: 20px 0 12px; }
    h4 { color: #666; font-size: 16px; margin: 16px 0 10px; }
    p { margin: 12px 0; }
    ul, ol { margin: 12px 0; padding-left: 24px; }
    li { margin: 6px 0; }
    strong { color: #ff2442; }
    .section { 
      margin: 32px 0; 
      padding: 24px; 
      background: white; 
      border-radius: 16px; 
      box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }
    .finding { 
      background: #fff5f5; 
      padding: 14px 18px; 
      margin: 10px 0; 
      border-radius: 10px; 
      border-left: 4px solid #ff2442; 
    }
    .images-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;
      margin: 20px 0;
    }
    .images-grid img {
      width: 100%;
      border-radius: 12px;
      object-fit: cover;
      aspect-ratio: 4/3;
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .images-grid img:hover {
      transform: scale(1.02);
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }
    .section-content { font-size: 15px; }
    .section-content h2 { font-size: 20px; }
    .section-content h3 { font-size: 17px; }
    footer { 
      text-align: center; 
      color: #999; 
      margin-top: 60px; 
      padding-top: 20px; 
      border-top: 1px solid #eee;
      font-size: 14px;
    }
    .meta { color: #888; font-size: 14px; margin-bottom: 24px; }
    
    /* Lightbox 样式 */
    .lightbox {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.9);
      z-index: 9999;
      align-items: center;
      justify-content: center;
      flex-direction: column;
    }
    .lightbox.active { display: flex; }
    .lightbox img {
      max-width: 90vw;
      max-height: 85vh;
      border-radius: 8px;
      object-fit: contain;
    }
    .lightbox-close {
      position: absolute;
      top: 20px;
      right: 30px;
      font-size: 40px;
      color: white;
      background: none;
      border: none;
      cursor: pointer;
      opacity: 0.7;
    }
    .lightbox-close:hover { opacity: 1; }
    .lightbox-nav {
      margin-top: 16px;
      display: flex;
      gap: 20px;
      align-items: center;
    }
    .lightbox-nav button {
      background: rgba(255,255,255,0.2);
      border: none;
      color: white;
      font-size: 24px;
      width: 50px;
      height: 50px;
      border-radius: 50%;
      cursor: pointer;
    }
    .lightbox-nav button:hover { background: rgba(255,255,255,0.3); }
    .lightbox-nav button:disabled { opacity: 0.3; cursor: not-allowed; }
    .lightbox-nav span { color: white; font-size: 14px; }
  </style>
</head>
<body>
  <h1>${report.topic}</h1>
  <p class="meta"><strong>生成时间：</strong>${new Date(report.createdAt).toLocaleString('zh-CN')}</p>
  
  ${report.summary ? `
    <div class="section">
      <h2>📋 研究摘要</h2>
      <p>${report.summary}</p>
    </div>
  ` : ''}
  
  ${report.keyFindings.length > 0 ? `
    <div class="section">
      <h2>✨ 关键发现</h2>
      ${report.keyFindings.map((f: string, i: number) => `<div class="finding">${i + 1}. ${f}</div>`).join('')}
    </div>
  ` : ''}
  
  ${report.sections.map((section: any, i: number) => `
    <div class="section">
      <h2>${i + 1}. ${section.title || `章节 ${i + 1}`}</h2>
      <div class="section-content">
        ${renderMarkdown(section.content)}
      </div>
      ${section.images && section.images.length > 0 ? `
        <div class="images-grid">
          ${section.images.map((img: string) => `<img src="${img}" referrerpolicy="no-referrer" loading="lazy" alt="研究配图" onclick="openLightbox('${img}')" />`).join('')}
        </div>
      ` : ''}
    </div>
  `).join('')}
  
  ${report.notes && report.notes.length > 0 ? `
    <div class="section">
      <h2>📚 数据来源</h2>
      <p style="color: #666; margin-bottom: 16px;">本研究基于 ${report.notes.length} 篇小红书笔记进行分析</p>
      <ul style="list-style: none; padding: 0;">
        ${report.notes.map((note: any) => `
          <li style="padding: 12px 16px; background: #f9f9f9; border-radius: 8px; margin-bottom: 8px;">
            <a href="${note.url}" target="_blank" rel="noopener" style="color: #ff2442; text-decoration: none; font-weight: 500;">
              ${note.title}
            </a>
            <div style="color: #888; font-size: 12px; margin-top: 4px;">
              ${note.author} · ❤️ ${note.likes}
            </div>
          </li>
        `).join('')}
      </ul>
    </div>
  ` : ''}
  
  <footer>
    由 RedNote Research Agent 生成 | 基于 ${report.notes?.length || 0} 篇笔记的深度分析
  </footer>
  
  <!-- Lightbox 图片查看器 -->
  <div id="lightbox" class="lightbox" onclick="closeLightbox()">
    <button class="lightbox-close" onclick="closeLightbox()">×</button>
    <img id="lightbox-img" src="" referrerpolicy="no-referrer" onclick="event.stopPropagation()" />
    <div class="lightbox-nav" onclick="event.stopPropagation()">
      <button onclick="prevImage()">‹</button>
      <span id="lightbox-counter"></span>
      <button onclick="nextImage()">›</button>
    </div>
  </div>
  
  <script>
    // 收集所有图片
    var images = Array.from(document.querySelectorAll('.images-grid img')).map(function(img) {
      return img.src;
    });
    var currentIndex = 0;
    
    function openLightbox(src) {
      currentIndex = images.indexOf(src);
      if (currentIndex === -1) currentIndex = 0;
      showImage();
      document.getElementById('lightbox').classList.add('active');
      document.body.style.overflow = 'hidden';
    }
    
    function closeLightbox() {
      document.getElementById('lightbox').classList.remove('active');
      document.body.style.overflow = '';
    }
    
    function showImage() {
      document.getElementById('lightbox-img').src = images[currentIndex];
      document.getElementById('lightbox-counter').textContent = (currentIndex + 1) + ' / ' + images.length;
    }
    
    function prevImage() {
      if (currentIndex > 0) {
        currentIndex--;
        showImage();
      }
    }
    
    function nextImage() {
      if (currentIndex < images.length - 1) {
        currentIndex++;
        showImage();
      }
    }
    
    // 键盘导航
    document.addEventListener('keydown', function(e) {
      if (!document.getElementById('lightbox').classList.contains('active')) return;
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') prevImage();
      if (e.key === 'ArrowRight') nextImage();
    });
  <\/script>
</body>
</html>`
}

const goBack = () => {
  router.push('/outline')
}

const goToPublish = () => {
  router.push('/publish/edit')
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
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  if (scrollHandler) {
    window.removeEventListener('scroll', scrollHandler)
  }
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
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

/* 导出下拉菜单 */
.export-dropdown {
  position: relative;
}

.export-dropdown .dropdown-arrow {
  margin-left: 4px;
  margin-right: 0;
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  overflow: hidden;
  z-index: 100;
  min-width: 140px;
}

.export-menu button {
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: none;
  text-align: left;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.export-menu button:hover {
  background: #f5f5f5;
}

.export-menu button:not(:last-child) {
  border-bottom: 1px solid #f0f0f0;
}

/* 小红书按钮 */
.btn-xiaohongshu {
  background: linear-gradient(135deg, #ff2442 0%, #ff6b81 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(255, 36, 66, 0.3);
}

.btn-xiaohongshu:hover {
  background: linear-gradient(135deg, #e6203a 0%, #ff5470 100%);
  box-shadow: 0 4px 12px rgba(255, 36, 66, 0.4);
  transform: translateY(-1px);
}

.btn-xiaohongshu svg {
  margin-right: 2px;
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

/* 笔记来源链接 */
.source-link {
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  color: var(--text-main);
  transition: color 0.2s;
}

.source-link:hover {
  color: var(--primary);
}

.source-link svg {
  opacity: 0;
  transition: opacity 0.2s;
}

.source-item:hover .source-link svg {
  opacity: 1;
}

/* Lightbox 图片查看器 */
.lightbox-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.lightbox-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 28px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

.lightbox-image {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.lightbox-nav {
  position: absolute;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 20px;
  background: rgba(255, 255, 255, 0.1);
  padding: 10px 24px;
  border-radius: 100px;
}

.lightbox-nav button {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.lightbox-nav button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.3);
}

.lightbox-nav button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.lightbox-nav span {
  color: white;
  font-size: 14px;
  min-width: 60px;
  text-align: center;
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
