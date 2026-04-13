import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/home.vue'
import stockRoutes from './stock'
import strategyRoutes from './strategy'
import userRoutes from './user'
import { useUserStore } from '@/stores/user'
import membershipRoutes from './membership'



const routes = [
  { path: '/',
    component: Home,
    Children:[]},
  ...stockRoutes,
  ...strategyRoutes,
  ...userRoutes,
  ...membershipRoutes,
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  // 检查路由是否需要权限
  if (to.meta.requiredLevel) {
    try {
      // 动态导入用户store，确保在Vue应用上下文中
      const userStore = useUserStore()

      // 如果用户未登录，重定向到登录页
      if (!userStore.isLoggedIn) {
        next('/login')
        return
      }

      // 检查用户权限
      if (!userStore.hasPermission(to.meta.requiredLevel)) {
        // 权限不足
        console.warn(`权限不足: 需要${to.meta.requiredLevel}权限，当前为${userStore.membershipLevel}`)
        // 可以跳转到权限不足页面或升级页面
        next('/upgrade') // 或者显示提示信息
        return
      }
    } catch (error) {
      console.error('权限检查出错:', error)
      // 出错时允许访问，避免阻止用户正常使用
      next()
      return
    }
  }

  next()
})
export default router
