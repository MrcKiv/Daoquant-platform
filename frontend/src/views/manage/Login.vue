<template>
  <div class="manage-login-page">
    <div class="manage-login-shell">
      <section class="manage-brand-panel">
        <p class="eyebrow">TAOTAO Admin</p>
        <h1>后台管理中心</h1>
        <p class="description">
          账号开通、级别分配和管理员入口统一在这里处理。
        </p>
      </section>

      <section class="manage-login-card">
        <h2>管理员登录</h2>
        <p class="subtext">只有 `admin` 级别账号可以进入后台管理页面。</p>

        <form class="login-form" @submit.prevent="handleLogin">
          <label>账号</label>
          <input v-model="form.usernumber" placeholder="请输入管理员账号" required />

          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="请输入密码" required />

          <button type="submit" :disabled="submitting">
            {{ submitting ? '登录中...' : '进入后台' }}
          </button>
        </form>

        <div class="actions">
          <router-link to="/login">普通用户登录</router-link>
          <router-link to="/">返回首页</router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const submitting = ref(false)
const form = reactive({
  usernumber: '',
  password: ''
})

const showClosableMessage = (type, message) => {
  ElMessage({
    type,
    message,
    showClose: true,
  })
}

onMounted(() => {
  if (userStore.hasPermission('admin')) {
    router.replace('/manage/users')
  }
})

const handleLogin = async () => {
  if (!form.usernumber || !form.password) {
    showClosableMessage('warning', '请输入管理员账号和密码')
    return
  }

  submitting.value = true
  try {
    const res = await axios.post('/api/user/admin/login/', {
      usernumber: form.usernumber,
      password: form.password
    }, {
      withCredentials: true
    })

    userStore.login({
      ...res.data.user,
      token: res.data.token
    })

    showClosableMessage('success', res.data.msg || '管理员登录成功')

    const redirect = router.currentRoute.value.query.redirect || '/manage/users'
    router.push(redirect)
  } catch (error) {
    showClosableMessage('error', error.response?.data?.msg || '管理员登录失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.manage-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
  background:
    radial-gradient(circle at top left, rgba(209, 67, 67, 0.16), transparent 36%),
    radial-gradient(circle at bottom right, rgba(17, 24, 39, 0.16), transparent 40%),
    linear-gradient(135deg, #f6efe9 0%, #f3f6fb 100%);
}

.manage-login-shell {
  width: min(1040px, 100%);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 28px 80px rgba(32, 41, 61, 0.14);
}

.manage-brand-panel {
  padding: 56px 48px;
  background: linear-gradient(160deg, #10233f 0%, #1e3d63 62%, #27496d 100%);
  color: #fff;
}

.eyebrow {
  margin: 0 0 14px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.7);
}

.manage-brand-panel h1 {
  margin: 0;
  font-size: 40px;
  line-height: 1.2;
}

.description {
  margin: 20px 0 0;
  max-width: 420px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.82);
}

.manage-login-card {
  padding: 56px 42px;
}

.manage-login-card h2 {
  margin: 0;
  font-size: 28px;
  color: #1f2937;
}

.subtext {
  margin: 12px 0 28px;
  color: #6b7280;
  line-height: 1.7;
}

.login-form {
  display: grid;
  gap: 12px;
}

.login-form label {
  font-size: 14px;
  color: #374151;
  font-weight: 600;
}

.login-form input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid #d9e0ea;
  border-radius: 14px;
  font-size: 15px;
  background: #f8fafc;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.login-form input:focus {
  border-color: #1e3d63;
  box-shadow: 0 0 0 3px rgba(30, 61, 99, 0.12);
}

.login-form button {
  margin-top: 10px;
  padding: 14px 18px;
  border: none;
  border-radius: 14px;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #10233f 0%, #d14343 100%);
  cursor: pointer;
}

.login-form button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.actions {
  margin-top: 22px;
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}

.actions a {
  color: #1e3d63;
  text-decoration: none;
  font-weight: 600;
}

@media (max-width: 860px) {
  .manage-login-shell {
    grid-template-columns: 1fr;
  }

  .manage-brand-panel,
  .manage-login-card {
    padding: 36px 24px;
  }

  .manage-brand-panel h1 {
    font-size: 30px;
  }
}
</style>
