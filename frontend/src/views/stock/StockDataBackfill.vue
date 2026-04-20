<template>
  <div class="stock-backfill-page">
    <FixedNavbar />

    <main class="page-shell">
      <section class="hero-card">
        <div class="hero-copy">
          <p class="eyebrow">Stock Data Ops</p>
          <h1>补全股票数据</h1>
          <p class="hero-desc">
            自动读取数据库最晚交易日和今天日期，调用
            <code>xtquant_backfill.py</code>
            或 Windows worker 补数服务
            对股票日线数据进行续传补全。
          </p>
        </div>

        <div class="hero-actions">
          <el-button
            type="primary"
            size="large"
            :loading="starting"
            :disabled="isBusy"
            @click="handleStart"
          >
            {{ isBusy ? '补全进行中' : '开始补全' }}
          </el-button>
          <el-button size="large" :loading="loading" @click="fetchStatus()">
            刷新状态
          </el-button>
        </div>
      </section>

      <section class="summary-grid">
        <article class="summary-card accent-blue">
          <span class="summary-label">数据库最晚日期</span>
          <strong class="summary-value">{{ databaseLatestText }}</strong>
          <span class="summary-hint">实时读取 {{ state.target_table || 'stock_1d' }} 当前最大 trade_date</span>
        </article>

        <article class="summary-card accent-gold">
          <span class="summary-label">今天日期</span>
          <strong class="summary-value">{{ state.today_date || '暂无' }}</strong>
          <span class="summary-hint">补全终点默认取系统当天日期</span>
        </article>

        <article class="summary-card accent-green">
          <span class="summary-label">本次补全区间</span>
          <strong class="summary-value">{{ rangeText }}</strong>
          <span class="summary-hint">{{ state.reason || '等待计算补全区间' }}</span>
        </article>

        <article class="summary-card accent-slate">
          <span class="summary-label">已写入记录</span>
          <strong class="summary-value">{{ formatNumber(state.saved_rows) }}</strong>
          <span class="summary-hint">失败批次 {{ formatNumber(state.failed_batches) }}</span>
        </article>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <span class="panel-kicker">Realtime Progress</span>
            <h2>任务进度</h2>
          </div>
          <span :class="['status-pill', `status-${state.status}`]">
            {{ statusLabel }}
          </span>
        </div>

        <el-progress
          :percentage="progressPercentage"
          :status="progressStatus"
          :stroke-width="18"
        />

        <div class="progress-meta">
          <span>{{ state.message || '等待开始补全任务。' }}</span>
          <strong>{{ progressPercentage.toFixed(0) }}%</strong>
        </div>

        <div class="detail-grid">
          <div class="detail-item">
            <span>已处理股票</span>
            <strong>{{ formatNumber(state.processed_stocks) }} / {{ formatNumber(state.total_stocks) }}</strong>
          </div>
          <div class="detail-item">
            <span>已处理批次</span>
            <strong>{{ formatNumber(state.processed_batches) }} / {{ formatNumber(state.total_batches) }}</strong>
          </div>
          <div class="detail-item">
            <span>当前股票</span>
            <strong>{{ state.current_stock || '--' }}</strong>
          </div>
          <div class="detail-item">
            <span>运行耗时</span>
            <strong>{{ elapsedText }}</strong>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head compact">
          <div>
            <span class="panel-kicker">Task Detail</span>
            <h2>任务详情</h2>
          </div>
        </div>

        <div class="info-list">
          <div class="info-row">
            <span>目标数据表</span>
            <strong>{{ state.target_table || 'stock_1d' }}</strong>
          </div>
          <div class="info-row">
            <span>执行方式</span>
            <strong>{{ executionModeText }}</strong>
          </div>
          <div class="info-row">
            <span>补数服务状态</span>
            <strong>{{ serviceStatusText }}</strong>
          </div>
          <div class="info-row">
            <span>补数服务地址</span>
            <strong>{{ state.service_url || '--' }}</strong>
          </div>
          <div class="info-row">
            <span>任务开始时间</span>
            <strong>{{ state.started_at || '--' }}</strong>
          </div>
          <div class="info-row">
            <span>任务结束时间</span>
            <strong>{{ state.finished_at || '--' }}</strong>
          </div>
          <div class="info-row">
            <span>当前库内最新日期</span>
            <strong>{{ state.database_latest_date_live || '--' }}</strong>
          </div>
          <div class="info-row">
            <span>上次批次新增</span>
            <strong>{{ formatNumber(state.last_batch_rows) }}</strong>
          </div>
          <div class="info-row">
            <span>失败信息</span>
            <strong class="error-text">{{ shortError }}</strong>
          </div>
        </div>

        <div
          :class="[
            'status-banner',
            state.status === 'failed' ? 'banner-error' : state.status === 'completed' ? 'banner-success' : 'banner-neutral'
          ]"
        >
          {{ bannerText }}
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import FixedNavbar from '@/components/common/FixedNavbar.vue'

const createInitialState = () => ({
  status: 'idle',
  phase: 'idle',
  message: '等待开始补全。',
  target_table: 'stock_1d',
  execution_mode: '',
  service_url: '',
  service_status: '',
  service_message: '',
  today_date: '',
  database_latest_date: '',
  database_latest_date_live: '',
  suggested_start_date: '',
  suggested_end_date: '',
  start_date: '',
  end_date: '',
  reason: '',
  progress_percent: 0,
  total_stocks: 0,
  processed_stocks: 0,
  total_batches: 0,
  processed_batches: 0,
  saved_rows: 0,
  last_batch_rows: 0,
  failed_batches: 0,
  current_stock: '',
  started_at: '',
  finished_at: '',
  elapsed_seconds: 0,
  last_error: ''
})

const state = ref(createInitialState())
const loading = ref(false)
const starting = ref(false)

let pollingTimer = null

const isBusy = computed(() => ['starting', 'running'].includes(state.value.status))

const progressPercentage = computed(() => {
  const raw = Number(state.value.progress_percent || 0)
  if (Number.isNaN(raw)) return 0
  return Math.min(100, Math.max(0, raw))
})

const progressStatus = computed(() => {
  if (state.value.status === 'failed') return 'exception'
  if (state.value.status === 'completed') {
    return state.value.failed_batches > 0 ? 'warning' : 'success'
  }
  return undefined
})

const statusLabel = computed(() => {
  const map = {
    idle: '待启动',
    starting: '启动中',
    running: '补全中',
    completed: '已完成',
    failed: '已失败'
  }
  return map[state.value.status] || '未知状态'
})

const databaseLatestText = computed(() => {
  return state.value.database_latest_date_live || state.value.database_latest_date || '暂无数据'
})

const rangeText = computed(() => {
  const start = state.value.start_date || state.value.suggested_start_date || '待计算'
  const end = state.value.end_date || state.value.suggested_end_date || state.value.today_date || '待计算'
  return `${start} -> ${end}`
})

const executionModeText = computed(() => {
  const map = {
    windows_host_service: 'Windows worker 补数服务',
    local_backend: '后端本地执行'
  }
  return map[state.value.execution_mode] || '未知执行方式'
})

const serviceStatusText = computed(() => {
  const map = {
    configured: '等待连接',
    connected: '已连接',
    local: '本地执行',
    unreachable: '无法连接',
    auth_failed: '鉴权失败',
    invalid_endpoint: '接口不匹配'
  }
  const label = map[state.value.service_status] || '未知状态'
  if (state.value.service_message) {
    return `${label} · ${state.value.service_message}`
  }
  return label
})

const elapsedText = computed(() => formatDuration(state.value.elapsed_seconds))

const shortError = computed(() => {
  if (!state.value.last_error) return '无'
  const firstLine = String(state.value.last_error).split('\n')[0]
  return firstLine.length > 120 ? `${firstLine.slice(0, 120)}...` : firstLine
})

const bannerText = computed(() => {
  if (state.value.status === 'completed') {
    return state.value.saved_rows > 0
      ? `补全完成，本次新增 ${formatNumber(state.value.saved_rows)} 条记录。`
      : '补全完成，数据库已是最新，没有新增记录。'
  }

  if (state.value.status === 'failed') {
    return state.value.message || '补全任务失败，请检查后台日志。'
  }

  if (isBusy.value) {
    return '任务正在后台执行中，页面会自动刷新进度。'
  }

  return '点击“开始补全”后，系统会自动从数据库最晚日期续传到今天。'
})

const normalizeState = (payload = {}) => ({
  ...createInitialState(),
  ...payload
})

const formatNumber = (value) => {
  const numeric = Number(value || 0)
  if (Number.isNaN(numeric)) return '0'
  return numeric.toLocaleString('zh-CN')
}

const formatDuration = (seconds) => {
  const totalSeconds = Number(seconds || 0)
  if (!totalSeconds) return '0 秒'

  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const remainSeconds = totalSeconds % 60

  const parts = []
  if (hours) parts.push(`${hours} 小时`)
  if (minutes) parts.push(`${minutes} 分钟`)
  if (remainSeconds || parts.length === 0) parts.push(`${remainSeconds} 秒`)
  return parts.join(' ')
}

const stopPolling = () => {
  if (pollingTimer) {
    window.clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const startPolling = () => {
  if (pollingTimer) return
  pollingTimer = window.setInterval(() => {
    fetchStatus({ silent: true })
  }, 2000)
}

const handleStatusTransition = (previousStatus, nextStatus) => {
  if (!['starting', 'running'].includes(previousStatus)) return

  if (nextStatus === 'completed') {
    ElMessage.success(state.value.message || '股票数据补全完成')
  } else if (nextStatus === 'failed') {
    ElMessage.error(state.value.message || '股票数据补全失败')
  }
}

const fetchStatus = async ({ silent = false } = {}) => {
  if (!silent) {
    loading.value = true
  }

  try {
    const previousStatus = state.value.status
    const response = await axios.get('/api/stock-backfill/status/', {
      withCredentials: true
    })

    state.value = normalizeState(response.data)
    handleStatusTransition(previousStatus, state.value.status)

    if (isBusy.value) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (error) {
    if (!silent) {
      ElMessage.error(error.response?.data?.error || '获取补数状态失败')
    }
    stopPolling()
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

const handleStart = async () => {
  starting.value = true

  try {
    const response = await axios.post(
      '/api/stock-backfill/start/',
      {},
      { withCredentials: true }
    )

    state.value = normalizeState(response.data?.state)
    ElMessage.success(response.data?.message || '补数任务已启动')
    startPolling()
  } catch (error) {
    const responseState = error.response?.data?.state
    if (responseState) {
      state.value = normalizeState(responseState)
    }

    if (error.response?.status === 409) {
      ElMessage.warning(error.response?.data?.message || '已有补数任务正在运行')
      startPolling()
    } else {
      ElMessage.error(error.response?.data?.error || error.response?.data?.message || '启动补数任务失败')
    }
  } finally {
    starting.value = false
  }
}

onMounted(async () => {
  await fetchStatus()
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.stock-backfill-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(39, 117, 255, 0.14), transparent 32%),
    radial-gradient(circle at top right, rgba(20, 184, 166, 0.12), transparent 28%),
    linear-gradient(180deg, #f5f8ff 0%, #eef3f8 100%);
  color: #1f2937;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.page-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 120px 24px 48px;
}

.hero-card,
.panel,
.summary-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
}

.hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 30px 32px;
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(240, 247, 255, 0.9));
  backdrop-filter: blur(12px);
}

.eyebrow,
.panel-kicker,
.summary-label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #64748b;
}

.hero-copy h1,
.panel-head h2 {
  margin: 8px 0 0;
  color: #0f172a;
}

.hero-copy h1 {
  font-size: clamp(30px, 4vw, 42px);
  line-height: 1.08;
}

.hero-desc {
  max-width: 640px;
  margin: 14px 0 0;
  font-size: 16px;
  line-height: 1.7;
  color: #475569;
}

.hero-desc code {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
  font-size: 14px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 22px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 152px;
  padding: 22px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
}

.summary-card::after {
  content: "";
  width: 56px;
  height: 4px;
  border-radius: 999px;
  margin-top: auto;
}

.accent-blue::after {
  background: linear-gradient(90deg, #2563eb, #38bdf8);
}

.accent-gold::after {
  background: linear-gradient(90deg, #d97706, #facc15);
}

.accent-green::after {
  background: linear-gradient(90deg, #059669, #2dd4bf);
}

.accent-slate::after {
  background: linear-gradient(90deg, #334155, #64748b);
}

.summary-value {
  font-size: 26px;
  line-height: 1.2;
  color: #0f172a;
}

.summary-hint {
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.panel {
  margin-top: 22px;
  padding: 26px 28px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.94);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-head.compact {
  margin-bottom: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 88px;
  padding: 10px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.status-idle {
  background: rgba(148, 163, 184, 0.14);
  color: #475569;
}

.status-starting,
.status-running {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.status-completed {
  background: rgba(5, 150, 105, 0.12);
  color: #047857;
}

.status-failed {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 14px;
  font-size: 14px;
  color: #475569;
}

.progress-meta strong {
  font-size: 22px;
  color: #0f172a;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 20px;
}

.detail-item,
.info-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(241, 245, 249, 0.96));
}

.detail-item {
  flex-direction: column;
}

.detail-item span,
.info-row span {
  font-size: 13px;
  color: #64748b;
}

.detail-item strong,
.info-row strong {
  font-size: 16px;
  color: #0f172a;
  word-break: break-word;
}

.info-list {
  display: grid;
  gap: 12px;
}

.status-banner {
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.7;
}

.banner-neutral {
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
}

.banner-success {
  background: rgba(5, 150, 105, 0.1);
  color: #047857;
}

.banner-error {
  background: rgba(220, 38, 38, 0.08);
  color: #b91c1c;
}

.error-text {
  color: #b91c1c;
}

@media (max-width: 1100px) {
  .summary-grid,
  .detail-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 840px) {
  .page-shell {
    padding: 104px 16px 36px;
  }

  .hero-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-actions {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .summary-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .panel,
  .hero-card {
    padding: 22px 18px;
    border-radius: 22px;
  }

  .panel-head,
  .progress-meta,
  .info-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-actions :deep(.el-button) {
    width: 100%;
  }
}
</style>
