<template>
  <header class="c-header">
    <div class="c-header-wrapper">
      <!-- 左侧部分：Logo + 专业版按钮 -->
      <div class="c-header-left">
        <div class="header-logo">内部自用</div>
        <a class="c-header-button" href="https://www.baidu.com" target="_blank">了解专业版</a>
      </div>

      <!-- 中间部分：导航菜单 -->
      <div class="c-header-center">
        <nav class="c-header-nav">
          <ul class="c-header-nav-ul">
            <li><router-link to="/">首页</router-link></li>

            <!-- 编写策略带下拉 -->
            <li class="dropdown">
              <a @click="checkAuthAndGo('/NewStrategy')" class="dropdown-trigger">
                编写策略
                <svg class="arrow" viewBox="0 0 1024 1024" width="10" height="10" xmlns="http://www.w3.org/2000/svg">
                  <path d="M512 640L192 320h640z" fill="currentColor"/>
                </svg>
              </a>
              <ul class="dropdown-menu">
                <li v-if="userStore.isLoggedIn">
                  <router-link to="/NewStrategy" class="nav-link">新建策略</router-link>
                </li>
                <li><a @click="checkAuthAndGo('/strategy-ai')" class="nav-link">AI策略助手</a></li>
              </ul>
            </li>

            <li v-if="userStore.isLoggedIn">
              <router-link to="/user-strategy">我的策略</router-link>
            </li>
          </ul>
        </nav>
      </div>

      <!-- 右侧按钮 -->
      <!-- 已登录 -->
      <div class="c-header-right" v-if="userStore.isLoggedIn">
        <div class="user-dropdown">
          <span class="user-name">
            欢迎，{{ userStore.user?.name || '用户' }}
            <span class="user-level" :class="userStore.membershipLevel">
              {{ getMembershipLevelText(userStore.membershipLevel) }}
            </span>
            <svg class="arrow" viewBox="0 0 1024 1024" width="10" height="10">
              <path d="M512 640L192 320h640z" fill="currentColor"/>
            </svg>
          </span>
          <ul class="dropdown-menu">
            <li><router-link to="/user-strategy">我的策略</router-link></li>
            <li><router-link to="/user/profile">个人资料</router-link></li>
            <li v-if="userStore.hasPermission('admin')"><router-link to="/manage/users">后台管理</router-link></li>
            <li><router-link to="/membership/upgrade">会员升级</router-link></li>
            <li><a @click.prevent="handleLogout">退出登录</a></li>
          </ul>
        </div>
      </div>

      <!-- 未登录 -->
      <div class="c-header-right" v-else>
        <router-link to="/login" class="btn-outline">登录</router-link>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'

const userStore = useUserStore()
const router = useRouter()

// 获取会员等级文本
const getMembershipLevelText = (level) => {
  const levelMap = {
    'free': '免费用户',
    'basic': '基础会员',
    'premium': '高级会员',
    'vip': 'VIP会员',
    'admin': '管理员'
  }
  return levelMap[level] || '免费用户'
}

const checkAuthAndGo = async (path) => {
  if (userStore.isLoggedIn) {
    router.push(path)
  } else {
    try {
      await ElMessageBox.confirm(
        '您尚未登录，是否前往登录页面？',
        '请先登录',
        {
          confirmButtonText: '去登录',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
      router.push('/login')
    } catch {
      // 用户点了"取消"，什么也不做
    }
  }
}

const handleLogout = async () => {
  try {
    await userStore.logout()

    ElMessage.success('退出登录成功')
    router.push('/')
  } catch (error) {
    console.error('登出失败:', error)
    ElMessage.error('登出失败')
  }
}
</script>

<style scoped>
@import '@/assets/css/common/FixedNavbar.css';

/* 添加会员等级样式 */
.user-level {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 12px;
  color: #fff;
  margin-left: 8px;
  vertical-align: middle;
}

.user-level.free {
  background-color: #909399;
}

.user-level.basic {
  background-color: #409EFF;
}

.user-level.premium {
  background-color: #67C23A;
}

.user-level.vip {
  background-color: #E6A23C;
}

.user-level.admin {
  background-color: #d14343;
}

/* 确保下拉菜单中的链接样式正确 */
.dropdown-menu a {
  display: block;
  padding: 8px 16px;
  color: #333;
  text-decoration: none;
}

.dropdown-menu a:hover {
  background-color: #f5f5f5;
}
</style>
