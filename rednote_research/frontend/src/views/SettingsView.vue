<template>
  <div class="settings-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-subtitle">配置 LLM 和 VLM 模型参数</p>
      </div>
    </div>
    
    <div class="settings-container">
      <!-- LLM 配置 -->
      <div class="settings-section card">
        <h2 class="section-title">
          🤖 LLM 配置
        </h2>
        
        <div class="form-group">
          <label class="form-label">API Key</label>
          <input 
            v-model="settings.llm.apiKey"
            type="password"
            class="form-input"
            placeholder="sk-..."
          />
        </div>
        
        <div class="form-group">
          <label class="form-label">Base URL</label>
          <input 
            v-model="settings.llm.baseUrl"
            type="text"
            class="form-input"
            placeholder="https://api-inference.modelscope.cn/v1"
          />
        </div>
        
        <div class="form-group">
          <label class="form-label">模型</label>
          <input 
            v-model="settings.llm.model"
            type="text"
            class="form-input"
            placeholder="gpt-4o 或自定义模型名称"
            list="llm-models"
          />
          <datalist id="llm-models">
            <option value="Qwen/Qwen3-235B-A22B-Thinking-2507">Qwen3 235B</option>
            <option value="Qwen/Qwen3-235B-A22B-Instruct-2507">Qwen3 235B</option>
            <option value="Qwen/Qwen2.5-72B-Instruct">Qwen2.5 72B</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4o-mini">GPT-4o Mini</option>
            <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
          </datalist>
          <p class="form-hint">可选择常用模型或输入自定义模型名称</p>
        </div>
        
        <button class="btn btn-secondary" @click="testLLM" :disabled="isTestingLLM">
          <span v-if="isTestingLLM" class="spinner-sm"></span>
          <span v-else>测试连接</span>
        </button>
        <span v-if="llmTestResult" class="test-result" :class="llmTestResult.success ? 'success' : 'error'">
          {{ llmTestResult.message }}
        </span>
      </div>
      
      <!-- VLM 配置 -->
      <div class="settings-section card">
        <h2 class="section-title">
          🖼️ VLM 配置（图片相关性验证）
        </h2>
        
        <div class="switch-container">
          <div>
            <div class="form-label" style="margin-bottom: 0;">启用图片验证</div>
            <p class="form-hint">使用 VLM 模型验证图片与分论点的相关性</p>
          </div>
          <div 
            class="switch" 
            :class="{ active: settings.vlm.enabled }"
            @click="settings.vlm.enabled = !settings.vlm.enabled"
          ></div>
        </div>
        
        <div v-if="settings.vlm.enabled">
          <div class="form-group">
            <label class="form-label">API Key</label>
            <input 
              v-model="settings.vlm.apiKey"
              type="password"
              class="form-input"
              placeholder="sk-..."
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">Base URL</label>
            <input 
              v-model="settings.vlm.baseUrl"
              type="text"
              class="form-input"
              placeholder="https://api-inference.modelscope.cn/v1"
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">VLM 模型</label>
            <input 
              v-model="settings.vlm.model"
              type="text"
              class="form-input"
              placeholder="qwen-vl-plus 或自定义模型名称"
              list="vlm-models"
            />
            <datalist id="vlm-models">
              <option value="Qwen/Qwen2.5-VL-32B-Instruct">Qwen2.5 VL 32B</option>
              <option value="Qwen/Qwen2-VL-7B-Instruct">Qwen2 VL 7B</option>
              <option value="qwen-vl-plus">Qwen-VL-Plus</option>
              <option value="qwen-vl-max">Qwen-VL-Max</option>
              <option value="gpt-4o">GPT-4o</option>
            </datalist>
            <p class="form-hint">可选择常用模型或输入自定义模型名称</p>
          </div>
          
          <button class="btn btn-secondary" @click="testVLM" :disabled="isTestingVLM">
            <span v-if="isTestingVLM" class="spinner-sm"></span>
            <span v-else>测试 VLM 连接</span>
          </button>
          <span v-if="vlmTestResult" class="test-result" :class="vlmTestResult.success ? 'success' : 'error'">
            {{ vlmTestResult.message }}
          </span>
          
          <div class="switch-container" style="margin-top: 20px;">
            <div>
              <div class="form-label" style="margin-bottom: 0;">稳定模式（防速率限制）</div>
              <p class="form-hint">开启后会串行处理+延迟，避免触发API频率限制；关闭则快速并行</p>
            </div>
            <div 
              class="switch" 
              :class="{ active: settings.vlm.rateLimitMode }"
              @click="settings.vlm.rateLimitMode = !settings.vlm.rateLimitMode"
            ></div>
          </div>
        </div>
      </div>
      
      <!-- 图片生成配置 -->
      <div class="settings-section card">
        <h2 class="section-title">
          🎨 图片生成配置（可选）
        </h2>
        
        <div class="switch-container">
          <div>
            <div class="form-label" style="margin-bottom: 0;">启用图片生成</div>
            <p class="form-hint">为不相关图片生成替换图（消耗较多 API 配额）</p>
          </div>
          <div 
            class="switch" 
            :class="{ active: settings.imageGen.enabled }"
            @click="settings.imageGen.enabled = !settings.imageGen.enabled"
          ></div>
        </div>
        
        <div v-if="settings.imageGen.enabled" style="margin-top: 20px;">
          <div class="form-group">
            <label class="form-label">API Key</label>
            <input 
              v-model="settings.imageGen.apiKey"
              type="password"
              class="form-input"
              placeholder="sk-..."
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">Base URL</label>
            <input 
              v-model="settings.imageGen.baseUrl"
              type="text"
              class="form-input"
              placeholder="https://api-inference.modelscope.cn/v1"
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">图片生成模型</label>
            <input 
              v-model="settings.imageGen.model"
              type="text"
              class="form-input"
              placeholder="wanx-v1 或自定义模型名称"
              list="imagegen-models"
            />
            <datalist id="imagegen-models">
              <option value="Tongyi-MAI/Z-Image-Turbo">Z-Image-Turbo</option>
              <option value="wanx-v1">通义万相 (wanx-v1)</option>
              <option value="flux-schnell">Flux Schnell</option>
              <option value="stable-diffusion-3">Stable Diffusion 3</option>
              <option value="dalle-3">DALL-E 3</option>
            </datalist>
            <p class="form-hint">可选择常用模型或输入自定义模型名称</p>
          </div>
          
          <button class="btn btn-secondary" @click="testImageGen" :disabled="isTestingImageGen">
            <span v-if="isTestingImageGen" class="spinner-sm"></span>
            <span v-else>测试图片生成</span>
          </button>
          <span v-if="imageGenTestResult" class="test-result" :class="imageGenTestResult.success ? 'success' : 'error'">
            {{ imageGenTestResult.message }}
          </span>
          
          <div class="switch-container" style="margin-top: 20px;">
            <div>
              <div class="form-label" style="margin-bottom: 0;">稳定模式（防速率限制）</div>
              <p class="form-hint">开启后会串行处理+延迟，避免触发API频率限制；关闭则快速并行</p>
            </div>
            <div 
              class="switch" 
              :class="{ active: settings.imageGen.rateLimitMode }"
              @click="settings.imageGen.rateLimitMode = !settings.imageGen.rateLimitMode"
            ></div>
          </div>
        </div>
      </div>
      
      <!-- MCP 连通性测试 & 二维码登录 -->
      <div class="settings-section card">
        <h2 class="section-title">
          🔗 小红书 MCP 连通性
        </h2>
        
        <!-- 登录状态 -->
        <div class="login-status" :class="mcpLoginStatus?.is_logged_in ? 'logged-in' : 'logged-out'">
          <span v-if="mcpLoginStatus?.is_logged_in">
            ✅ 已登录：{{ mcpLoginStatus.username || '未知用户' }}
          </span>
          <span v-else>
            ⚠️ 未登录小红书
          </span>
        </div>
        
        <div class="mcp-actions">
          <button class="btn btn-secondary" @click="testMCP" :disabled="isTestingMCP">
            <span v-if="isTestingMCP" class="spinner-sm"></span>
            <span v-else>测试连接</span>
          </button>
          
          <button 
            class="btn btn-primary" 
            @click="getQRCode" 
            :disabled="isGettingQRCode || mcpLoginStatus?.is_logged_in"
          >
            <span v-if="isGettingQRCode" class="spinner-sm"></span>
            <span v-else>获取登录二维码</span>
          </button>
        </div>
        
        <span v-if="mcpTestResult" class="test-result" :class="mcpTestResult.success ? 'success' : 'error'">
          {{ mcpTestResult.message }}
        </span>
        
        <!-- 二维码显示区域 -->
        <div v-if="qrCodeData" class="qrcode-container">
          <img :src="qrCodeData.img" alt="登录二维码" class="qrcode-img" />
          <p class="qrcode-hint">请使用小红书 App 扫码登录</p>
          <p class="qrcode-timeout">有效期: {{ qrCodeData.timeout }}</p>
          <button class="btn btn-link" @click="qrCodeData = null">关闭</button>
        </div>
      </div>
      
      <!-- 搜索配置 -->
      <div class="settings-section card">
        <h2 class="section-title">
          🔍 搜索配置
        </h2>
        
        <div class="form-group">
          <label class="form-label">每个关键词搜索笔记数量</label>
          <input 
            v-model.number="settings.search.notesPerKeyword"
            type="number"
            class="form-input"
            min="1"
            max="20"
            placeholder="1"
          />
          <p class="form-hint">
            每个关键词最多搜索多少篇笔记（范围 1-20，默认 1）。增大可提高研究深度，但会增加处理时间。
          </p>
        </div>
      </div>
      
      <!-- 保存按钮 -->
      <div class="settings-actions">
        <button class="btn btn-primary" @click="saveSettings" :disabled="isSaving">
          <span v-if="isSaving" class="spinner"></span>
          <span v-else>保存设置</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface Settings {
  llm: {
    apiKey: string
    baseUrl: string
    model: string
  }
  vlm: {
    enabled: boolean
    apiKey: string
    baseUrl: string
    model: string
    rateLimitMode: boolean
  }
  imageGen: {
    enabled: boolean
    apiKey: string
    baseUrl: string
    model: string
    rateLimitMode: boolean
  }
  search: {
    notesPerKeyword: number
  }
}

const settings = ref<Settings>({
  llm: {
    apiKey: '',
    baseUrl: 'https://api-inference.modelscope.cn/v1',
    model: 'Qwen/Qwen3-235B-A22B-Thinking-2507'
  },
  vlm: {
    enabled: false,
    apiKey: '',
    baseUrl: 'https://api-inference.modelscope.cn/v1',
    model: 'Qwen/Qwen2.5-VL-32B-Instruct',
    rateLimitMode: true
  },
  imageGen: {
    enabled: false,
    apiKey: '',
    baseUrl: 'https://api-inference.modelscope.cn/v1',
    model: 'Tongyi-MAI/Z-Image-Turbo',
    rateLimitMode: true
  },
  search: {
    notesPerKeyword: 1
  }
})

const isTestingLLM = ref(false)
const isSaving = ref(false)
const llmTestResult = ref<{ success: boolean; message: string } | null>(null)

const loadSettings = async () => {
  try {
    const response = await axios.get('/api/settings')
    if (response.data) {
      settings.value = { ...settings.value, ...response.data }
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
}

const saveSettings = async () => {
  isSaving.value = true
  try {
    await axios.post('/api/settings', settings.value)
    alert('设置已保存')
  } catch (error) {
    alert('保存失败，请重试')
  } finally {
    isSaving.value = false
  }
}

const testLLM = async () => {
  isTestingLLM.value = true
  llmTestResult.value = null
  
  try {
    const response = await axios.post('/api/settings/test', {
      apiKey: settings.value.llm.apiKey,
      baseUrl: settings.value.llm.baseUrl,
      model: settings.value.llm.model
    })
    llmTestResult.value = { success: true, message: '连接成功！' }
  } catch (error: any) {
    const detail = error.response?.data?.detail || '连接失败，请检查配置'
    llmTestResult.value = { success: false, message: detail }
  } finally {
    isTestingLLM.value = false
  }
}

// VLM 测试
const isTestingVLM = ref(false)
const vlmTestResult = ref<{ success: boolean; message: string } | null>(null)

const testVLM = async () => {
  isTestingVLM.value = true
  vlmTestResult.value = null
  
  try {
    const response = await axios.post('/api/settings/test-vlm', {
      apiKey: settings.value.vlm.apiKey,
      baseUrl: settings.value.vlm.baseUrl,
      model: settings.value.vlm.model
    })
    vlmTestResult.value = { success: true, message: response.data.message || 'VLM 连接成功！' }
  } catch (error: any) {
    const detail = error.response?.data?.detail || 'VLM 连接失败，请检查配置'
    vlmTestResult.value = { success: false, message: detail }
  } finally {
    isTestingVLM.value = false
  }
}

// 图片生成模型测试
const isTestingImageGen = ref(false)
const imageGenTestResult = ref<{ success: boolean; message: string } | null>(null)

const testImageGen = async () => {
  isTestingImageGen.value = true
  imageGenTestResult.value = null
  
  try {
    const response = await axios.post('/api/settings/test-imagegen', {
      apiKey: settings.value.imageGen.apiKey,
      baseUrl: settings.value.imageGen.baseUrl,
      model: settings.value.imageGen.model
    })
    imageGenTestResult.value = { success: true, message: response.data.message || '图片生成模型连接成功！' }
  } catch (error: any) {
    const detail = error.response?.data?.detail || '图片生成模型连接失败，请检查配置'
    imageGenTestResult.value = { success: false, message: detail }
  } finally {
    isTestingImageGen.value = false
  }
}

// MCP 连通性测试
const isTestingMCP = ref(false)
const mcpTestResult = ref<{ success: boolean; message: string } | null>(null)
const mcpLoginStatus = ref<{ is_logged_in: boolean; username: string } | null>(null)
const qrCodeData = ref<{ img: string; timeout: string } | null>(null)
const isGettingQRCode = ref(false)
let loginPollTimer: number | null = null

const testMCP = async () => {
  isTestingMCP.value = true
  mcpTestResult.value = null
  
  try {
    const response = await axios.post('/api/settings/test-mcp')
    mcpTestResult.value = { success: true, message: response.data.message || 'MCP 连接成功！' }
    // 刷新登录状态
    await checkLoginStatus()
  } catch (error: any) {
    const detail = error.response?.data?.detail || 'MCP 连接失败，请检查配置'
    mcpTestResult.value = { success: false, message: detail }
  } finally {
    isTestingMCP.value = false
  }
}

const checkLoginStatus = async () => {
  try {
    const response = await axios.get('/api/mcp/login/status')
    if (response.data.success) {
      mcpLoginStatus.value = response.data.data
    }
  } catch (error) {
    console.error('获取登录状态失败:', error)
  }
}

const getQRCode = async () => {
  isGettingQRCode.value = true
  qrCodeData.value = null
  
  try {
    const response = await axios.get('/api/mcp/login/qrcode')
    if (response.data.success) {
      const data = response.data.data
      if (data.is_logged_in) {
        mcpLoginStatus.value = { is_logged_in: true, username: '' }
        mcpTestResult.value = { success: true, message: '已登录！' }
      } else {
        qrCodeData.value = data
        // 开始轮询登录状态
        startLoginPoll()
      }
    }
  } catch (error: any) {
    const detail = error.response?.data?.detail || '获取二维码失败'
    mcpTestResult.value = { success: false, message: detail }
  } finally {
    isGettingQRCode.value = false
  }
}

const startLoginPoll = () => {
  if (loginPollTimer) {
    clearInterval(loginPollTimer)
  }
  
  loginPollTimer = window.setInterval(async () => {
    await checkLoginStatus()
    if (mcpLoginStatus.value?.is_logged_in) {
      qrCodeData.value = null
      mcpTestResult.value = { success: true, message: '登录成功！' }
      if (loginPollTimer) {
        clearInterval(loginPollTimer)
        loginPollTimer = null
      }
    }
  }, 3000)
  
  // 4分钟后停止轮询
  setTimeout(() => {
    if (loginPollTimer) {
      clearInterval(loginPollTimer)
      loginPollTimer = null
    }
  }, 240000)
}

onMounted(() => {
  loadSettings()
  checkLoginStatus()
})
</script>

<style scoped>
.settings-view {
  max-width: 700px;
  margin: 0 auto;
}

.settings-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  padding: 28px;
}

.form-hint {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.test-result {
  margin-left: 16px;
  font-size: 14px;
}

.test-result.success {
  color: var(--log-success);
}

.test-result.error {
  color: var(--log-error);
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(0,0,0,0.1);
  border-radius: 50%;
  border-top-color: var(--text-main);
  animation: spin 1s ease-in-out infinite;
}

/* MCP 登录状态 */
.login-status {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: 500;
}

.login-status.logged-in {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.login-status.logged-out {
  background: rgba(234, 179, 8, 0.1);
  color: #eab308;
}

.mcp-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

/* 二维码容器 */
.qrcode-container {
  margin-top: 20px;
  padding: 24px;
  background: var(--bg-secondary);
  border-radius: 12px;
  text-align: center;
}

.qrcode-img {
  max-width: 240px;
  border-radius: 12px;
  border: 4px solid white;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.qrcode-hint {
  margin-top: 16px;
  font-size: 15px;
  color: var(--text-main);
}

.qrcode-timeout {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.btn-link {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  margin-top: 12px;
}

.btn-link:hover {
  text-decoration: underline;
}
</style>
