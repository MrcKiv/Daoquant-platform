<template>
  <div class="home-container">
    <FixedNavbar />
    <div>
      <Third />
      <Lastone />
    </div>
  </div>
</template>

<script setup>
import FixedNavbar from '@/components/common/FixedNavbar.vue'
import Third from '@/components/common/Third.vue'
import Lastone from '@/components/common/Lastone.vue'

import { onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(async () => {
  try {
    const res = await axios.get('/api/user/check_login/', {
      withCredentials: true
    })

    if (res.data.is_login) {
      console.log('用户已登录:', res.data)
      userStore.login(res.data.user)
      ElMessage.success(`欢迎回来，用户 : ${res.data.user.name}`)
    } else {
      ElMessage.warning('您尚未登录')
    }
  } catch (err) {
    console.error('登录状态检查失败:', err)
    ElMessage.error('无法获取登录状态')
  }
})

</script>
