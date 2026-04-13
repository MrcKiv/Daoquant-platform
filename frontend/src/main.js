import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import 'vue3-carousel/dist/carousel.css'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

/* ================================
 * axios 全局配置（唯一正确方式）
 * ================================ */

axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL || ''
axios.defaults.withCredentials = true

// 使用 axios 内建 CSRF 机制（不要再手动改 header）
axios.defaults.xsrfCookieName = 'csrftoken'
axios.defaults.xsrfHeaderName = 'X-CSRFToken'

axios.defaults.headers.post['Content-Type'] = 'application/json'

/* ================================
 * 初始化 CSRF（只做一件事：写 cookie）
 * ================================ */
async function initCSRF() {
  try {
    await axios.get('/api/strategy/csrf_token/')
    console.log('[CSRF] initialized')
  } catch (e) {
    console.warn('[CSRF] init failed', e)
  }
}

/* ================================
 * 创建应用
 * ================================ */

const app = createApp(App)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

app.use(pinia)
app.use(router)
app.use(ElementPlus)

  /* ================================
   * 启动前先初始化 CSRF
   * ================================ */
  ; (async () => {
    await initCSRF()
    app.mount('#app')
  })()
