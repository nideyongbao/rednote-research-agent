<template>
  <div class="publish-result-view">
    <div class="result-container">
      <!-- 发布中状态 -->
      <div v-if="status === 'publishing'" class="result-card publishing">
        <div class="loading-animation">
          <div class="spinner"></div>
        </div>
        <h2>正在发布到小红书...</h2>
        <div class="publish-logs">
          <div 
            v-for="(log, index) in logs" 
            :key="index" 
            class="log-item"
          >
            {{ log }}
          </div>
        </div>
      </div>

      <!-- 发布成功 -->
      <div v-else-if="status === 'success'" class="result-card success">
        <div class="result-icon">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#52c41a" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <h2>发布成功！🎉</h2>
        <p class="result-desc">你的小红书笔记已成功发布</p>
        
        <div class="success-info">
          <div class="info-item">
            <span class="label">笔记标题</span>
            <span class="value">{{ draft.title }}</span>
          </div>
          <div v-if="draft.published_url" class="info-item">
            <span class="label">笔记链接</span>
            <a :href="draft.published_url" target="_blank" class="link">
              {{ draft.published_url }}
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                <polyline points="15 3 21 3 21 9"/>
                <line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </a>
          </div>
        </div>

        <div class="action-buttons">
          <a 
            v-if="draft.published_url" 
            :href="draft.published_url" 
            target="_blank"
            class="btn btn-primary"
          >
            查看笔记
          </a>
          <button class="btn btn-secondary" @click="goToHome">
            返回首页
          </button>
        </div>
      </div>

      <!-- 发布失败 -->
      <div v-else-if="status === 'failed'" class="result-card failed">
        <div class="result-icon">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#ff4d4f" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        </div>
        <h2>发布失败</h2>
        <p class="result-desc error-msg">{{ errorMessage }}</p>
        
        <div class="publish-logs" v-if="logs.length > 0">
          <h4>发布日志</h4>
          <div 
            v-for="(log, index) in logs" 
            :key="index" 
            class="log-item"
          >
            {{ log }}
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn btn-primary" @click="retry">
            重试发布
          </button>
          <button class="btn btn-secondary" @click="goBack">
            返回编辑
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const status = ref<'publishing' | 'success' | 'failed'>('publishing')
const draft = ref({
  id: '',
  title: '',
  published_url: ''
})
const logs = ref<string[]>([])
const errorMessage = ref('')

onMounted(() => {
  const draftId = route.params.draftId as string
  if (draftId) {
    draft.value.id = draftId
    executePublish(draftId)
  } else {
    router.push('/report')
  }
})

async function executePublish(draftId: string) {
  status.value = 'publishing'
  logs.value = []
  
  try {
    const eventSource = new EventSource(`/api/publish/${draftId}/execute`)
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'log') {
        logs.value.push(data.message)
      } else if (data.type === 'complete') {
        eventSource.close()
        
        if (data.success) {
          draft.value = data.data
          status.value = 'success'
        } else {
          draft.value = data.data
          errorMessage.value = data.data?.error || '发布失败'
          status.value = 'failed'
        }
      } else if (data.type === 'error') {
        eventSource.close()
        errorMessage.value = data.message
        status.value = 'failed'
      }
    }
    
    eventSource.onerror = () => {
      eventSource.close()
      errorMessage.value = '连接中断，请检查网络'
      status.value = 'failed'
    }
  } catch (error) {
    console.error('Publish error:', error)
    errorMessage.value = String(error)
    status.value = 'failed'
  }
}

function retry() {
  if (draft.value.id) {
    executePublish(draft.value.id)
  }
}

function goBack() {
  router.push({ 
    name: 'publish-edit', 
    params: { draftId: draft.value.id } 
  })
}

function goToHome() {
  router.push('/')
}
</script>

<style scoped>
.publish-result-view {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.result-container {
  width: 100%;
  max-width: 500px;
}

.result-card {
  background: white;
  border-radius: 24px;
  padding: 48px 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.result-card h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-main);
  margin: 24px 0 12px;
}

.result-desc {
  font-size: 15px;
  color: #666;
  margin: 0 0 32px;
}

.error-msg {
  color: #ff4d4f;
}

/* 加载动画 */
.loading-animation {
  margin-bottom: 16px;
}

.spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #f0f0f0;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 结果图标 */
.result-icon {
  margin-bottom: 8px;
}

/* 成功信息 */
.success-info {
  background: #f9f9f9;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 32px;
  text-align: left;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item .label {
  font-size: 12px;
  color: #999;
}

.info-item .value {
  font-size: 14px;
  color: var(--text-main);
  font-weight: 500;
}

.info-item .link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--primary);
  text-decoration: none;
  font-size: 14px;
  word-break: break-all;
}

.info-item .link:hover {
  text-decoration: underline;
}

/* 发布日志 */
.publish-logs {
  background: #f9f9f9;
  border-radius: 12px;
  padding: 16px;
  margin: 24px 0;
  text-align: left;
  max-height: 200px;
  overflow-y: auto;
}

.publish-logs h4 {
  font-size: 13px;
  color: #999;
  margin: 0 0 12px;
}

.log-item {
  font-size: 13px;
  color: #666;
  padding: 4px 0;
  font-family: monospace;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn {
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover {
  background: #e6203a;
}

.btn-secondary {
  background: #f5f5f5;
  color: var(--text-main);
}

.btn-secondary:hover {
  background: #eee;
}

/* 响应式 */
@media (max-width: 560px) {
  .result-card {
    padding: 32px 24px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
