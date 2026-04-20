import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'
import Home from '@/views/home.vue'
import strategyRoutes from './strategy'
import userRoutes from './user'
import manageRoutes from './manage'
import { useUserStore } from '@/stores/user'
import membershipRoutes from './membership'



const routes = [
  { path: '/',
    component: Home,
    Children:[]},
  ...strategyRoutes,
  ...userRoutes,
  ...manageRoutes,
  ...membershipRoutes,
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  if (!to.meta.requiredLevel) {
    next()
    return
  }

  const userStore = useUserStore()

  try {
    if (!userStore.isLoggedIn) {
      const res = await axios.get('/api/user/check_login/', {
        withCredentials: true
      })

      if (res.data.is_login) {
        userStore.login(res.data.user)
      }
    }
  } catch (error) {
    userStore.clearAuthState()
  }

  if (!userStore.isLoggedIn) {
    next({
      path: to.meta.loginPath || '/login',
      query: { redirect: to.fullPath }
    })
    return
  }

  if (!userStore.hasPermission(to.meta.requiredLevel)) {
    console.warn(`权限不足: 需要${to.meta.requiredLevel}权限，当前为${userStore.membershipLevel}`)
    next(to.meta.requiredLevel === 'admin' ? '/' : '/upgrade')
    return
  }

  next()
})
export default router
