<template>
  <div class="compare-view">
    <div class="page-header">
      <h1 class="page-title">研究对比分析</h1>
      <button class="btn btn-secondary" @click="$router.back()">返回</button>
    </div>

    <div v-if="loading" class="loading-state">
      正在进行对比分析...
    </div>

    <div v-else-if="result" class="comparison-content">
      <div class="comparison-header">
        <div class="record-card left">
          <h3>{{ result.records[0].topic }}</h3>
          <span class="time">{{ formatDate(result.records[0].time) }}</span>
        </div>
        <div class="vs-badge">VS</div>
        <div class="record-card right">
          <h3>{{ result.records[1].topic }}</h3>
          <span class="time">{{ formatDate(result.records[1].time) }}</span>
        </div>
      </div>

      <div class="analysis-section">
        <h2>{{ result.comparison.summary }}</h2>
        
        <div class="comparison-grid">
          <div class="grid-item">
            <h3>{{ result.records[0].topic }} 核心发现</h3>
            <ul>
              <li v-for="(item, i) in result.comparison.unique_findings_1" :key="i">{{ item }}</li>
            </ul>
          </div>
          <div class="grid-item">
            <h3>{{ result.records[1].topic }} 核心发现</h3>
            <ul>
              <li v-for="(item, i) in result.comparison.unique_findings_2" :key="i">{{ item }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const loading = ref(true)
const result = ref<any>(null)

const formatDate = (isoStr: string) => {
  return new Date(isoStr).toLocaleString()
}

onMounted(async () => {
  const ids = route.query.ids as string
  if (!ids) return
  
  try {
    const recordIds = ids.split(',')
    const response = await axios.post('/api/history/compare', { record_ids: recordIds })
    result.value = response.data
  } catch (e) {
    console.error(e)
    alert("对比分析失败")
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.compare-view {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #333;
}
.comparison-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
  margin-bottom: 40px;
}
.record-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  width: 300px;
  text-align: center;
}
.record-card h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
}
.vs-badge {
  font-size: 24px;
  font-weight: bold;
  color: #ff2442;
  background: #fff0f2;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.comparison-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
.grid-item {
  background: white;
  padding: 24px;
  border-radius: 12px;
}
.grid-item ul {
  padding-left: 20px;
  line-height: 1.6;
}
</style>
