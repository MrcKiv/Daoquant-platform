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
      if (state.user.membership_level === 'admin') return true
      if (state.user.membership_level === 'free') return false

      if (state.user.membership_expiry) {
        const expiryDate = new Date(state.user.membership_expiry)
        return expiryDate > new Date()
      }
      return true
    },

    isAdmin: (state) => {
      return state.user?.membership_level === 'admin'
    }
  },

  actions: {
    login(userData) {
      this.user = userData
      this.isLoggedIn = true
    },

    clearAuthState() {
      this.user = null
      this.isLoggedIn = false
    },

    async logout() {
      try {
        await axios.post('/api/user/logout/', {}, {
          withCredentials: true
        })
      } catch (error) {
        console.warn('后端登出失败，已清理本地登录状态', error)
      } finally {
        this.clearAuthState()
      }
    },

    updateUserInfo(userData) {
      if (this.user) {
        this.user = { ...this.user, ...userData }
      } else {
        this.user = userData
      }
    },

    hasPermission(requiredLevel) {
      if (!this.user) return false

      const levelHierarchy = {
        'free': 0,
        'basic': 1,
        'premium': 2,
        'vip': 3,
        'admin': 4
      }

      let userLevel = this.user.membership_level
      if (userLevel === 'admin') {
        return true
      }

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
