import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'

// Styles
import './assets/css/variables.css'
import './assets/css/base.css'
import './assets/css/components.css'
import './assets/css/research.css'

const app = createApp(App)

// 配置 Pinia 持久化插件
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

app.use(pinia)
app.use(router)

app.mount('#app')

