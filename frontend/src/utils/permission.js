// utils/permission.js
import { useUserStore } from '@/stores/user'

// 异步获取用户store的函数
export const getUserStore = async () => {
  // 确保在Vue应用上下文中使用store
  const { useUserStore } = await import('@/stores/user')
  return useUserStore()
}

// 权限检查函数
export const checkPermission = async (requiredLevel) => {
  try {
    const userStore = useUserStore()
    return userStore.hasPermission(requiredLevel)
  } catch (error) {
    console.error('权限检查失败:', error)
    return false
  }
}

// 检查是否已登录
export const checkLogin = async () => {
  try {
    const userStore = useUserStore()
    return userStore.isLoggedIn
  } catch (error) {
    console.error('登录检查失败:', error)
    return false
  }
}
