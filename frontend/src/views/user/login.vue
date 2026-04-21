<template>
  <FixedNavbar />
  <div class="auth-bg">
    <div class="auth-card">
      <h2 class="title">用户登录</h2>
      <form @submit.prevent="login">
        <label>账号</label>
        <input v-model="usernumber" maxlength="20" placeholder="请输入账号" required />

        <label>密码</label>
        <input v-model="password" type="password" placeholder="请输入密码" required />

        <button type="submit">登录</button>
      </form>

      <p class="links">
        账号由管理员统一开通
      </p>
      <p class="forgot">
        <router-link to="/reset">忘记密码？</router-link>
      </p>
      <p class="forgot">
        <router-link to="/manage/login">管理员登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FixedNavbar from '@/components/common/FixedNavbar.vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const usernumber = ref('')
const password = ref('')

const showClosableMessage = (type, message) => {
  ElMessage({
    type,
    message,
    showClose: true,
  })
}

const login = async () => {
  if (!/^[A-Za-z0-9]+$/.test(usernumber.value)) {
    showClosableMessage('warning', '账号只能包含数字和大小写字母')
    return
  }

  try {
    const res = await axios.post('/api/user/login/', {
      usernumber: usernumber.value,
      password: password.value,
    }, {
      withCredentials: true
    })

    userStore.login({
      ...res.data.user,
      token: res.data.token,
    })

    showClosableMessage('success', res.data.msg || '登录成功')

    const redirect = router.currentRoute.value.query.redirect || '/'
    router.push(redirect)
  } catch (e) {
    showClosableMessage('error', e.response?.data?.msg || '登录失败，请检查账号或密码')
  }
}
</script>

<style scoped>
@import '../../assets/css/user/login.css';

.links {
  color: #666;
}
</style>
