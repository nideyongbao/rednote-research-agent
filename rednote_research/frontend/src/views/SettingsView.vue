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
            placeholder="https://api.openai.com/v1"
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
            <option value="gpt-4o"></option>
            <option value="gpt-4o-mini"></option>
            <option value="qwen-plus"></option>
            <option value="qwen-max"></option>
            <option value="qwen-turbo"></option>
            <option value="Qwen/Qwen3-235B-A22B-Thinking-2507"></option>
            <option value="claude-3-5-sonnet"></option>
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
              placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">VLM 模型</label>
            <select v-model="settings.vlm.model" class="form-select">
              <option value="qwen-vl-plus">Qwen-VL-Plus</option>
              <option value="qwen-vl-max">Qwen-VL-Max</option>
              <option value="gpt-4o">GPT-4o</option>
            </select>
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
              placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">图片生成模型</label>
            <select v-model="settings.imageGen.model" class="form-select">
              <option value="wanx-v1">通义万相 (wanx-v1)</option>
              <option value="flux-schnell">Flux Schnell</option>
              <option value="stable-diffusion-3">Stable Diffusion 3</option>
              <option value="dalle-3">DALL-E 3</option>
            </select>
          </div>
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
  }
  imageGen: {
    enabled: boolean
    apiKey: string
    baseUrl: string
    model: string
  }
}

const settings = ref<Settings>({
  llm: {
    apiKey: '',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4o'
  },
  vlm: {
    enabled: false,
    apiKey: '',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen-vl-plus'
  },
  imageGen: {
    enabled: false,
    apiKey: '',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'wanx-v1'
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
  } catch (error) {
    llmTestResult.value = { success: false, message: '连接失败，请检查配置' }
  } finally {
    isTestingLLM.value = false
  }
}

onMounted(() => {
  loadSettings()
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
</style>
