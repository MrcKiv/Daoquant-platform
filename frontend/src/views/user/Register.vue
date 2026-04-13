<template>
  <FixedNavbar />
  <div class="auth-bg">
    <div class="auth-card">
      <h2 class="title">用户注册</h2>
      <form @submit.prevent="register">
        <label>用户名</label>
        <input v-model="name" placeholder="请输入用户名" required />

        <label>账号</label>
        <input v-model="usernumber" placeholder="请输入11位账号" required />

        <label>密码</label>
        <input v-model="password" type="password" placeholder="请输入密码" required />

        <label>确认密码</label>
        <input v-model="confirmPassword" type="password" placeholder="请再次输入密码" required />

        <button type="submit">注册</button>
      </form>

      <p class="links">
        已有账号？
        <router-link to="/login" class="btn-outline">立即登录</router-link>
      </p>
      <p class="forgot">
        <router-link to="/reset">忘记密码？</router-link>
      </p>
    </div>
  </div>
  <Lastone />
</template>

<script setup>
import FixedNavbar from '@/components/common/FixedNavbar.vue'
import Lastone from '@/components/common/Lastone.vue'
import { ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus' //  引入 ElMessage

const router = useRouter()
const usernumber = ref('')
const password = ref('')
const confirmPassword = ref('')
const name = ref('')

const register = async () => {
  if (!/^\d{11}$/.test(usernumber.value)) {
    ElMessage.warning('账号必须是11位纯数字')
    return
  }

  if (password.value !== confirmPassword.value) {
    ElMessage.error('两次输入的密码不一致')
    return
  }

  try {
    const res = await axios.post('/api/user/register/', {
      usernumber: usernumber.value,
      password: password.value,
      name: name.value,
    })
    ElMessage.success(res.data.msg || '注册成功')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '注册失败')
  }
}
</script>

<style scoped>
@import '@/assets/css/user/Register.css';
</style>
