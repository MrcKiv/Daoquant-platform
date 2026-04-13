// // src/stores/user.js
// import { defineStore } from 'pinia'
//
// export const useUserStore = defineStore('user', {
//   state: () => ({
//     isLoggedIn: false,
//     userInfo: null
//   }),
//   actions: {
//     login(user) {
//       this.isLoggedIn = true
//       this.userInfo = user
//     },
//     logout() {
//       this.isLoggedIn = false
//       this.userInfo = null
//     }
//   },
//   persist: true
// })
// stores/user.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    isLoggedIn: false
  }),

  getters: {
    membershipLevel: (state) => {
      return state.user ? state.user.membership_level : 'free'
    },

    isVipActive: (state) => {
      if (!state.user) return false
      // 检查会员是否过期
      if (state.user.membership_expiry) {
        const expiryDate = new Date(state.user.membership_expiry)
        return expiryDate > new Date()
      }
      return true
    }
  },

  actions: {
    // 用户登录
    login(userData) {
      this.user = userData
      this.isLoggedIn = true
    },

    // 用户登出
    logout() {
      this.user = null
      this.isLoggedIn = false
      // 可以调用后端登出接口
      // axios.post('/api/user/logout/', {}, { withCredentials: true })
    },

    // 更新用户信息
    updateUserInfo(userData) {
      if (this.user) {
        this.user = { ...this.user, ...userData }
      } else {
        this.user = userData
      }
    },

    // 权限检查方法
    hasPermission(requiredLevel) {
      if (!this.user) return false

      const levelHierarchy = {
        'free': 0,
        'basic': 1,
        'premium': 2,
        'vip': 3
      }

      // 如果会员已过期，降级为免费用户
      let userLevel = this.user.membership_level
      if (!this.isVipActive && userLevel !== 'free') {
        userLevel = 'free'
      }

      const userLevelValue = levelHierarchy[userLevel] || 0
      const requiredLevelValue = levelHierarchy[requiredLevel] || 0

      return userLevelValue >= requiredLevelValue
    }
  },

  // 持久化存储
  persist: {
    key: 'user-store',
    storage: localStorage,
    paths: ['user', 'isLoggedIn']
  }
})
