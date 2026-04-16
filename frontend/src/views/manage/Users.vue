<template>
  <div class="manage-users-page">
    <header class="manage-header">
      <div>
        <p class="eyebrow">TAOTAO Admin</p>
        <h1>账号管理</h1>
        <p class="description">创建账号、分配级别，并限制只有 `admin` 级别账号可进入后台。</p>
      </div>

      <div class="header-actions">
        <button class="ghost-btn" @click="goHome">返回首页</button>
        <button class="danger-btn" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <main class="manage-content">
      <section class="panel create-panel">
        <div class="panel-title">
          <h2>新增账号</h2>
          <p>新增账号统一使用 11 位数字账号。</p>
        </div>

        <form class="create-form" @submit.prevent="handleCreateUser">
          <label>用户名</label>
          <input v-model="form.name" placeholder="请输入用户名" required />

          <label>账号</label>
          <input v-model="form.usernumber" maxlength="20" placeholder="请输入11位数字账号" required />

          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="请输入密码" required />

          <label>账号级别</label>
          <select v-model="form.membership_level">
            <option v-for="level in membershipLevels" :key="level.value" :value="level.value">
              {{ level.label }}
            </option>
          </select>

          <button type="submit" :disabled="submitting">
            {{ submitting ? '创建中...' : '创建账号' }}
          </button>
        </form>
      </section>

      <section class="panel list-panel">
        <div class="panel-title">
          <h2>账号列表</h2>
          <p>当前共 {{ users.length }} 个账号。</p>
        </div>

        <div class="table-wrap" v-loading="loading">
          <el-table :data="users" border stripe>
            <el-table-column prop="name" label="用户名" min-width="140" />
            <el-table-column prop="usernumber" label="账号" min-width="140" />
            <el-table-column label="当前级别" min-width="120">
              <template #default="{ row }">
                <el-tag :type="tagTypeMap[row.membership_level] || 'info'">
                  {{ levelLabelMap[row.membership_level] || row.membership_level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="调整级别" min-width="220">
              <template #default="{ row }">
                <div class="level-editor">
                  <el-select v-model="row.nextLevel" size="small">
                    <el-option
                      v-for="level in membershipLevels"
                      :key="level.value"
                      :label="level.label"
                      :value="level.value"
                    />
                  </el-select>
                  <el-button
                    size="small"
                    type="primary"
                    :disabled="row.nextLevel === row.membership_level"
                    @click="updateMembershipLevel(row)"
                  >
                    保存
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const membershipLevels = ref([])

const form = reactive({
  name: '',
  usernumber: '',
  password: '',
  membership_level: 'free'
})

const tagTypeMap = {
  free: 'info',
  basic: 'primary',
  premium: 'success',
  vip: 'warning',
  admin: 'danger'
}

const levelLabelMap = computed(() => {
  return membershipLevels.value.reduce((acc, level) => {
    acc[level.value] = level.label
    return acc
  }, {})
})

const normalizeUsers = (rawUsers) => {
  users.value = rawUsers.map((user) => ({
    ...user,
    nextLevel: user.membership_level
  }))
}

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/user/admin/users/', {
      withCredentials: true
    })

    membershipLevels.value = res.data.membership_levels || []
    normalizeUsers(res.data.users || [])
  } catch (error) {
    ElMessage.error(error.response?.data?.error || error.response?.data?.msg || '加载账号列表失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.name = ''
  form.usernumber = ''
  form.password = ''
  form.membership_level = 'free'
}

const handleCreateUser = async () => {
  if (!/^\d{11}$/.test(form.usernumber)) {
    ElMessage.warning('新增账号必须是11位纯数字')
    return
  }

  submitting.value = true
  try {
    const res = await axios.post('/api/user/admin/users/', {
      name: form.name,
      usernumber: form.usernumber,
      password: form.password,
      membership_level: form.membership_level
    }, {
      withCredentials: true
    })

    ElMessage.success(res.data.msg || '账号创建成功')
    resetForm()
    await loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || '账号创建失败')
  } finally {
    submitting.value = false
  }
}

const updateMembershipLevel = async (row) => {
  try {
    const res = await axios.patch(`/api/user/admin/users/${row.id}/membership/`, {
      membership_level: row.nextLevel
    }, {
      withCredentials: true
    })

    row.membership_level = row.nextLevel

    if (userStore.user?.id === row.id) {
      userStore.updateUserInfo({
        membership_level: row.nextLevel
      })
    }

    ElMessage.success(res.data.msg || '账号级别更新成功')
  } catch (error) {
    row.nextLevel = row.membership_level
    ElMessage.error(error.response?.data?.msg || '账号级别更新失败')
  }
}

const formatDate = (value) => {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

const goHome = () => {
  router.push('/')
}

const handleLogout = async () => {
  await userStore.logout()
  router.push('/manage/login')
}

onMounted(async () => {
  if (!userStore.hasPermission('admin')) {
    router.replace('/manage/login')
    return
  }

  await loadUsers()
})
</script>

<style scoped>
.manage-users-page {
  min-height: 100vh;
  padding: 28px;
  background:
    linear-gradient(180deg, rgba(16, 35, 63, 0.06) 0%, rgba(16, 35, 63, 0) 18%),
    linear-gradient(135deg, #f4f7fb 0%, #f8efe7 100%);
}

.manage-header {
  max-width: 1320px;
  margin: 0 auto 24px;
  padding: 28px 32px;
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  border-radius: 24px;
  background: #10233f;
  color: #fff;
  box-shadow: 0 18px 50px rgba(16, 35, 63, 0.16);
}

.eyebrow {
  margin: 0 0 12px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.66);
}

.manage-header h1 {
  margin: 0;
  font-size: 34px;
}

.description {
  margin: 12px 0 0;
  color: rgba(255, 255, 255, 0.78);
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.ghost-btn,
.danger-btn {
  border: none;
  border-radius: 14px;
  padding: 12px 18px;
  cursor: pointer;
  font-weight: 700;
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}

.danger-btn {
  background: #d14343;
  color: #fff;
}

.manage-content {
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 24px;
}

.panel {
  background: rgba(255, 255, 255, 0.94);
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 18px 45px rgba(25, 39, 62, 0.08);
}

.panel-title h2 {
  margin: 0;
  font-size: 24px;
  color: #111827;
}

.panel-title p {
  margin: 10px 0 0;
  color: #6b7280;
  line-height: 1.7;
}

.create-form {
  margin-top: 24px;
  display: grid;
  gap: 12px;
}

.create-form label {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.create-form input,
.create-form select {
  width: 100%;
  padding: 13px 14px;
  border: 1px solid #d8dee8;
  border-radius: 14px;
  background: #f8fafc;
  outline: none;
}

.create-form button {
  margin-top: 10px;
  border: none;
  border-radius: 14px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #10233f 0%, #d14343 100%);
  color: #fff;
  cursor: pointer;
  font-weight: 700;
}

.create-form button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.table-wrap {
  margin-top: 24px;
}

.level-editor {
  display: flex;
  gap: 10px;
  align-items: center;
}

@media (max-width: 1100px) {
  .manage-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .manage-users-page {
    padding: 16px;
  }

  .manage-header,
  .panel {
    padding: 22px 18px;
  }

  .manage-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .manage-header h1 {
    font-size: 28px;
  }

  .level-editor {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
