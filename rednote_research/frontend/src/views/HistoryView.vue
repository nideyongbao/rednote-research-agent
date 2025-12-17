<template>
  <div class="history-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">历史记录</h1>
        <p class="page-subtitle">查看过往的研究报告</p>
      </div>
      <div class="header-actions">
        <div class="search-box">
          <input 
            v-model="searchKeyword"
            type="text"
            placeholder="搜索研究主题..."
            @keyup.enter="handleSearch"
          />
          <button class="search-btn" @click="handleSearch">🔍</button>
        </div>
      </div>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
    
    <!-- 历史列表 -->
    <div class="history-list" v-else-if="historyItems.length > 0">
      <div 
        v-for="item in historyItems" 
        :key="item.id"
        class="history-item"
        @click="viewDetail(item)"
      >
        <div class="item-icon">
          <span v-if="item.status === 'completed'">✅</span>
          <span v-else-if="item.status === 'running'">🔄</span>
          <span v-else-if="item.status === 'failed'">❌</span>
          <span v-else>📋</span>
        </div>
        <div class="item-content">
          <h3 class="item-title">{{ item.topic }}</h3>
          <p class="item-meta">
            <span class="item-date">{{ formatDate(item.created_at) }}</span>
            <span class="item-status" :class="item.status">{{ statusText(item.status) }}</span>
            <span v-if="item.notes_count" class="item-stat">{{ item.notes_count }} 篇笔记</span>
            <span v-if="item.sections_count" class="item-stat">{{ item.sections_count }} 个章节</span>
          </p>
          <p v-if="item.summary" class="item-summary">{{ item.summary }}</p>
        </div>
        <button class="item-delete" @click.stop="deleteItem(item.id)" title="删除">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>
      
      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <button 
          class="page-btn" 
          :disabled="currentPage <= 1"
          @click="changePage(currentPage - 1)"
        >
          上一页
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button 
          class="page-btn" 
          :disabled="currentPage >= totalPages"
          @click="changePage(currentPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div class="empty-state" v-else>
      <div class="empty-icon">📋</div>
      <h3>暂无历史记录</h3>
      <p>开始一个新的研究任务吧</p>
      <button class="btn btn-primary" @click="goHome">开始研究</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

interface HistoryItem {
  id: string
  topic: string
  status: string
  created_at: string
  updated_at: string
  summary?: string
  notes_count: number
  sections_count: number
}

const historyItems = ref<HistoryItem[]>([])
const isLoading = ref(false)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = 10
const searchKeyword = ref('')

const statusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '待处理',
    running: '进行中',
    completed: '已完成',
    failed: '失败'
  }
  return statusMap[status] || status
}

const formatDate = (dateStr: string) => {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

const loadHistory = async (page: number = 1) => {
  isLoading.value = true
  try {
    const response = await axios.get('/api/history', {
      params: { page, page_size: pageSize }
    })
    historyItems.value = response.data.items || []
    totalPages.value = response.data.total_pages || 1
    currentPage.value = page
  } catch (error) {
    console.error('加载历史记录失败:', error)
    historyItems.value = []
  } finally {
    isLoading.value = false
  }
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    loadHistory(1)
    return
  }
  
  isLoading.value = true
  try {
    const response = await axios.get('/api/history/search', {
      params: { keyword: searchKeyword.value, limit: 20 }
    })
    historyItems.value = response.data || []
    totalPages.value = 1
    currentPage.value = 1
  } catch (error) {
    console.error('搜索失败:', error)
  } finally {
    isLoading.value = false
  }
}

const changePage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    loadHistory(page)
  }
}

const viewDetail = (item: HistoryItem) => {
  // 如果已完成，跳转到报告页面
  if (item.status === 'completed') {
    router.push({ path: '/report', query: { id: item.id } })
  } else {
    router.push({ path: '/research', query: { id: item.id } })
  }
}

const deleteItem = async (id: string) => {
  if (!confirm('确定要删除这条记录吗？')) return
  
  try {
    await axios.delete(`/api/history/${id}`)
    historyItems.value = historyItems.value.filter(item => item.id !== id)
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败，请重试')
  }
}

const goHome = () => {
  router.push('/')
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.history-view {
  max-width: 900px;
  margin: 0 auto;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.search-box {
  display: flex;
  background: white;
  border-radius: 100px;
  padding: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.search-box input {
  border: none;
  padding: 8px 16px;
  font-size: 14px;
  width: 200px;
  background: transparent;
}

.search-box input:focus {
  outline: none;
}

.search-btn {
  background: none;
  border: none;
  padding: 8px 12px;
  cursor: pointer;
}

.loading-state {
  text-align: center;
  padding: 60px 20px;
}

.loading-state .spinner {
  width: 32px;
  height: 32px;
  margin: 0 auto 16px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: white;
  padding: 20px 24px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.history-item:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}

.item-icon {
  font-size: 24px;
  padding-top: 4px;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 6px;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.item-status {
  padding: 2px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 500;
}

.item-status.completed {
  background: #E8F5E9;
  color: #2E7D32;
}

.item-status.running {
  background: #FFF3E0;
  color: #E65100;
}

.item-status.pending {
  background: #E3F2FD;
  color: #1565C0;
}

.item-status.failed {
  background: #FFEBEE;
  color: #C62828;
}

.item-stat {
  color: var(--text-secondary);
}

.item-summary {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.item-delete {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s;
}

.item-delete:hover {
  color: #FF4D4F;
  background: #FFF1F0;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
}

.page-btn {
  padding: 8px 16px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: var(--text-secondary);
}

.empty-state {
  text-align: center;
  padding: 80px 20px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-size: 20px;
  color: var(--text-main);
  margin-bottom: 8px;
}

.empty-state p {
  color: var(--text-secondary);
  margin-bottom: 24px;
}
</style>
