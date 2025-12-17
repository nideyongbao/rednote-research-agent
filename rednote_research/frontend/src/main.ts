import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Styles
import './assets/css/variables.css'
import './assets/css/base.css'
import './assets/css/components.css'
import './assets/css/research.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
