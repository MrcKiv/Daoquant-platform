<!--<template>-->
<!--  <FixedNavbar />-->
<!--  <div class="auth-bg">-->
<!--    <div class="auth-card">-->
<!--      <h2 class="title">用户登录</h2>-->
<!--      <form @submit.prevent="login">-->
<!--        <label>账号</label>-->
<!--        <input v-model="usernumber" placeholder="请输入11位账号" required />-->

<!--        <label>密码</label>-->
<!--        <input v-model="password" type="password" placeholder="请输入密码" required />-->

<!--        <button type="submit">登录</button>-->
<!--      </form>-->

<!--      <p class="links">-->
<!--        没有账号？-->
<!--        <router-link to="/register" class="btn-outline">立即注册</router-link>-->
<!--      </p>-->
<!--      <p class="forgot">-->
<!--        <router-link to="/reset">忘记密码？</router-link>-->
<!--      </p>-->
<!--    </div>-->
<!--  </div>-->
<!--  <Lastone />-->
<!--</template>-->

<!--<script setup>-->
<!--import FixedNavbar from '@/components/common/FixedNavbar.vue'-->
<!--import Lastone from '@/components/common/Lastone.vue'-->
<!--import { ref } from 'vue'-->
<!--import axios from 'axios'-->
<!--import { useRouter } from 'vue-router'-->
<!--import { ElMessage } from 'element-plus'-->
<!--import { useUserStore } from '@/stores/user' // ✅ 引入 Pinia 用户 store-->

<!--const router = useRouter()-->
<!--const userStore = useUserStore() // ✅ 获取 store 实例-->

<!--const usernumber = ref('')-->
<!--const password = ref('')-->

<!--const login = async () => {-->
<!--  if (!/^\d{11}$/.test(usernumber.value)) {-->
<!--    ElMessage.warning('账号必须是11位纯数字')-->
<!--    return-->
<!--  }-->

<!--  try {-->
<!--    const res = await axios.post('/api/user/login/', {-->
<!--      usernumber: usernumber.value,-->
<!--      password: password.value,-->
<!--    }, {-->
<!--      withCredentials: true-->
<!--    })-->

<!--    const userData = res.data.user  // 假设后端返回了 user 对象和 token-->
<!--    const token = res.data.token-->

<!--    // ✅ 存储用户状态-->
<!--    userStore.login({-->
<!--      ...userData,-->
<!--      token: token, // 如果你希望在 store 中持久化 token-->
<!--    })-->

<!--    ElMessage.success(res.data.msg || '登录成功')-->
<!--    router.push('/')-->
<!--  } catch (e) {-->
<!--    ElMessage.error(e.response?.data?.msg || '登录失败，请检查账号或密码')-->
<!--  }-->
<!--}-->
<!--</script>-->

<!--<style scoped>-->
<!--@import  '../../assets/css/user/login.css';-->
<!--</style>-->
<!-- views/user/login.vue -->
<template>
  <FixedNavbar />
  <div class="auth-bg">
    <div class="auth-card">
      <h2 class="title">用户登录</h2>
      <form @submit.prevent="login">
        <label>账号</label>
        <input v-model="usernumber" placeholder="请输入11位账号" required />

        <label>密码</label>
        <input v-model="password" type="password" placeholder="请输入密码" required />

        <button type="submit">登录</button>
      </form>

      <p class="links">
        没有账号？
        <router-link to="/register" class="btn-outline">立即注册</router-link>
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
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const usernumber = ref('')
const password = ref('')

const login = async () => {
  if (!/^\d{11}$/.test(usernumber.value)) {
    ElMessage.warning('账号必须是11位纯数字')
    return
  }

  try {
    const res = await axios.post('/api/user/login/', {
      usernumber: usernumber.value,
      password: password.value,
    }, {
      withCredentials: true
    })

    const userData = res.data.user
    const token = res.data.token

    // 更新用户Store
    userStore.login({
      ...userData,
      token: token,
    })

    ElMessage.success(res.data.msg || '登录成功')

    // 登录成功后跳转到首页或其他页面
    const redirect = router.currentRoute.value.query.redirect || '/'
    router.push(redirect)
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '登录失败，请检查账号或密码')
  }
}
</script>

<style scoped>
@import  '../../assets/css/user/login.css';
</style>
