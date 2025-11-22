import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

// Import du thème custom (IMPORTANT : avant element-plus)
import './styles/theme.css'
import './styles/main.scss'

const app = createApp(App)
const pinia = createPinia()

// Enregistrer toutes les icônes Element Plus
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)

// Initialiser le store auth avant le montage
const authStore = useAuthStore()
authStore.initialize().then(() => {
  app.mount('#app')
})