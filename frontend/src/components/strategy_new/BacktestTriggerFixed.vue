<template>
  <div class="backtest-trigger">
    <div class="toolbar">
      <button class="start-backtest-btn" @click="startBacktest">开始回测</button>
      <button :disabled="isPreparingReport" @click="openPreparedReport">
        {{ isPreparingReport ? '报告准备中...' : '导出 PDF 报告' }}
      </button>
    </div>

    <div class="content-grid">
      <section class="summary-panel">
        <h3>回测概览</h3>
        <table class="summary-table">
          <tbody>
            <tr v-for="item in summaryData" :key="item.label">
              <th>{{ item.label }}</th>
              <td>{{ item.value }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="chart-panel">
        <h3>收益趋势图</h3>
        <div v-if="chartError" class="chart-error">{{ chartError }}</div>
        <div ref="chartRef" class="chart-canvas"></div>
      </section>
    </div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import axios from 'axios'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const strategyName = route.params.id
const autoTradeEnabled = import.meta.env.VITE_ENABLE_AUTO_TRADE === 'true'
const tradeApiBaseUrl = (import.meta.env.VITE_TRADE_API_BASE_URL || '/trade-api').replace(/\/$/, '')

const props = defineProps({
  params: {
    type: Object,
    required: true,
    default: () => ({
      strategy: {},
      selector: {},
      factor: {},
    }),
  },
})

const chartRef = ref(null)
const chartError = ref('')
const strategyConfig = ref({})
const factorConfig = ref([])
const selectorConfig = ref([])
const backtestResultData = ref({})
const backtestConfigResult = ref({})
const requestData = ref({ incomeBase: '沪深300' })
const isPreparingReport = ref(false)

let chartInstance = null

const REPORT_DATA_KEYS = [
  'daily_returns',
  'period_returns',
  'annual_returns',
  'stock_performance_attribution_range',
  'stock_performance_attribution_loss_range',
  'industry_allocation_timeline',
  'holdings_timeline',
  'industry_holdings_analysis',
  'end_period_market_value_proportion',
  'transaction_type_analysis',
  'transaction_type_analysis_sell',
  'calculate_stock_profit_loss',
  'metrics',
]

const getSnapshotKey = name => `daoquant:last-backtest:${name || strategyName || 'unknown'}`

const parseMaybeJson = (value, fallback) => {
  if (value == null || value === '') return fallback
  if (Array.isArray(value) || typeof value === 'object') return value
  try {
    return JSON.parse(value)
  } catch {
    try {
      return JSON.parse(String(value).replace(/'/g, '"'))
    } catch {
      return fallback
    }
  }
}

const normalizeBacktestResult = (data = {}) => ({
  ...data,
  dates: Array.isArray(data.dates) ? data.dates : [],
  benchmarkReturns: Array.isArray(data.benchmarkReturns) ? data.benchmarkReturns : [],
  strategyReturns: Array.isArray(data.strategyReturns) ? data.strategyReturns : [],
  ShareHolding_stock: data.ShareHolding_stock || {},
  trades: data.trades || {},
})

const extractBacktestResult = (payload = {}) => {
  if (payload?.backtest_result) return payload.backtest_result
  if (payload?.backtestResult) return payload.backtestResult
  if (Array.isArray(payload?.dates) || Array.isArray(payload?.benchmarkReturns) || Array.isArray(payload?.strategyReturns)) {
    return payload
  }
  return {}
}

const hasBacktestPayload = result => Array.isArray(result?.dates) && result.dates.length > 0

const hasFullReportData = result => {
  if (!hasBacktestPayload(result)) return false
  return REPORT_DATA_KEYS.every(key => Object.prototype.hasOwnProperty.call(result, key))
}

const persistLatestBacktest = result => {
  const name = currentStrategy.value?.strategyName || strategyName
  if (!name || !hasBacktestPayload(result)) return

  const snapshot = {
    strategyName: name,
    strategyConfig: currentStrategy.value || {},
    factorConfig: currentFactor.value || [],
    selectorConfig: currentSelector.value || [],
    backtestResult: result,
    savedAt: Date.now(),
  }

  sessionStorage.setItem(getSnapshotKey(name), JSON.stringify(snapshot))
}

const restoreLatestBacktest = () => {
  const name = currentStrategy.value?.strategyName || strategyName
  if (!name) return false

  const raw = sessionStorage.getItem(getSnapshotKey(name))
  if (!raw) return false

  try {
    const snapshot = JSON.parse(raw)
    strategyConfig.value = snapshot.strategyConfig || strategyConfig.value
    factorConfig.value = snapshot.factorConfig || []
    selectorConfig.value = snapshot.selectorConfig || []
    backtestResultData.value = normalizeBacktestResult(snapshot.backtestResult || {})
    requestData.value.incomeBase = snapshot.strategyConfig?.benchmark || requestData.value.incomeBase
    return hasBacktestPayload(backtestResultData.value)
  } catch (error) {
    console.error('restoreLatestBacktest error:', error)
    return false
  }
}

const currentStrategy = computed(() => ({ ...strategyConfig.value, ...props.params.strategy }))

const currentSelector = computed(() => {
  const incoming = props.params.selector?.received_data?.conditions
  return Array.isArray(incoming) && incoming.length > 0 ? incoming : selectorConfig.value
})

const currentFactor = computed(() => {
  const incoming = props.params.factor?.received_data?.factors
  return Array.isArray(incoming) && incoming.length > 0 ? incoming : factorConfig.value
})

const chartData = computed(() => {
  if (hasBacktestPayload(backtestResultData.value)) return backtestResultData.value
  return backtestConfigResult.value
})

const summaryData = computed(() => {
  const s = currentStrategy.value || {}
  const factorStr = (currentFactor.value || [])
    .map(item => `${item.name || item.factor || ''}${item.operator || ''}${item.value ?? ''}`)
    .join('，')
  const selector = currentSelector.value?.[0] || {}

  return [
    { label: '策略名称', value: s.strategyName || strategyName || '-' },
    { label: '初始资金', value: s.capital ? `${s.capital}万元` : '-' },
    { label: '持股比例', value: s.ratio ? `${s.ratio}%` : '-' },
    { label: '持股数目', value: s.hold || '-' },
    { label: '收益基准', value: s.benchmark || '-' },
    { label: '时间范围', value: s.start_date && s.end_date ? `${s.start_date} 至 ${s.end_date}` : '-' },
    { label: '因子', value: factorStr || '-' },
    { label: '策略选择', value: selector.operator || '-' },
  ]
})

const tradeDates = computed(() => chartData.value?.dates || [])
const benchmarkSeries = computed(() => (chartData.value?.benchmarkReturns || []).slice(0, tradeDates.value.length).map(v => Number(v) * 100))
const strategySeries = computed(() => (chartData.value?.strategyReturns || []).slice(0, tradeDates.value.length).map(v => Number(v) * 100))
const shareholdingMap = computed(() => chartData.value?.ShareHolding_stock || {})

const resizeChart = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

const initChart = () => {
  if (!chartRef.value || tradeDates.value.length === 0) {
    return
  }

  chartError.value = ''

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)
  const benchmarkName = currentStrategy.value?.benchmark || requestData.value.incomeBase || 'Benchmark'

  chartInstance.setOption({
    title: { text: '收益趋势图' },
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        if (!params?.length) return ''
        const date = params[0].name
        const holdings = shareholdingMap.value?.[date] || []
        const lines = params.map(item => `${item.seriesName}: ${item.value}%`)
        return [
          `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`,
          ...lines,
          holdings.length ? `当日持仓: ${holdings.join(', ')}` : '当日持仓: 空仓',
        ].join('<br/>')
      },
    },
    legend: { data: [benchmarkName, 'Strategy'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: tradeDates.value },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: benchmarkName,
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: benchmarkSeries.value,
        lineStyle: { color: '#d94f4f', width: 2 },
        itemStyle: { color: '#d94f4f' },
      },
      {
        name: 'Strategy',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: strategySeries.value,
        lineStyle: { color: '#2563eb', width: 2 },
        itemStyle: { color: '#2563eb' },
      },
    ],
  }, true)

  chartInstance.resize()
}

const applyBacktestResult = async rawResult => {
  const normalized = normalizeBacktestResult(rawResult)
  backtestResultData.value = normalized
  props.params.trade_date = normalized.dates
  props.params.income_base_price = normalized.benchmarkReturns.map(v => Number(v) * 100)
  props.params.backData = normalized.strategyReturns.map(v => Number(v) * 100)
  props.params.ShareHolding_stock = normalized.ShareHolding_stock
  props.params.TradeData = normalized.trades

  if (!hasBacktestPayload(normalized)) {
    return false
  }

  await nextTick()
  initChart()
  return true
}

const loadStrategySummary = async () => {
  const name = props.params.strategy?.strategyName || strategyName
  if (!name) return null

  const res = await axios.post('/api/strategy/loadStrategySummary/', { strategyName: name }, { withCredentials: true })
  if (!res.data?.success) {
    return null
  }

  strategyConfig.value = res.data.backtest_config || {}
  Object.assign(props.params.strategy, res.data.backtest_config || {})

  factorConfig.value = parseMaybeJson(res.data.backtest_config?.bottomfactor, [])
  selectorConfig.value = parseMaybeJson(res.data.backtest_config?.optionfactor, [])
  requestData.value.incomeBase = res.data.backtest_config?.benchmark || '沪深300'

  const loadedBacktestResult = extractBacktestResult(res.data)
  backtestConfigResult.value = normalizeBacktestResult(loadedBacktestResult)

  if (hasBacktestPayload(backtestConfigResult.value)) {
    await nextTick()
    initChart()
    persistLatestBacktest(backtestConfigResult.value)
  }

  return backtestConfigResult.value
}

const loadFullReportData = async () => {
  const name = props.params.strategy?.strategyName || strategyName
  if (!name) return null

  const res = await axios.post('/api/strategy/loadStrategyConfig/', { strategyName: name }, { withCredentials: true })
  if (!res.data?.success) {
    return null
  }

  strategyConfig.value = res.data.backtest_config || strategyConfig.value
  factorConfig.value = parseMaybeJson(res.data.backtest_config?.bottomfactor, factorConfig.value)
  selectorConfig.value = parseMaybeJson(res.data.backtest_config?.optionfactor, selectorConfig.value)

  const loadedBacktestResult = extractBacktestResult(res.data)
  return normalizeBacktestResult(loadedBacktestResult)
}

const sendAutoTradeData = async (trades, strategyNo) => {
  if (!autoTradeEnabled) return

  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  const todayTransactions = trades?.[today] || []
  const tradeData = todayTransactions
    .map(transaction => {
      const operate = transaction.trade_type === '买入' ? 'buy' : transaction.trade_type === '卖出' ? 'sell' : ''
      if (!operate) return null
      const code = (transaction.st_code || '').split('.')[0]
      return {
        strategy_no: strategyNo,
        code,
        name: code,
        ct_amount: transaction.number_of_transactions,
        operate,
        price: transaction.trade_price || 0,
      }
    })
    .filter(Boolean)

  if (tradeData.length > 0) {
    await axios.post(`${tradeApiBaseUrl}/queue`, tradeData)
  }
}

const startBacktest = async () => {
  try {
    if (!currentStrategy.value?.strategyName) {
      ElMessage.error('请先选择策略')
      return
    }

    chartError.value = ''

    const payload = {
      strategy: {
        strategyName: currentStrategy.value.strategyName || '',
        capital: Number(currentStrategy.value.capital ?? 0),
        ratio: Number(currentStrategy.value.ratio ?? 100),
        hold: Number(currentStrategy.value.hold ?? 10),
        start_date: currentStrategy.value.start_date || '2025-01-01',
        end_date: currentStrategy.value.end_date || '2025-12-31',
      },
      selector: {
        received_data: {
          conditions: currentSelector.value || [],
        },
      },
      factor: {
        received_data: {
          factors: currentFactor.value || [],
        },
      },
    }

    const response = await axios.post('/api/strategy/getBackTrigger/', payload)
    const immediateResult = normalizeBacktestResult(extractBacktestResult(response.data))
    const latestResult = await loadStrategySummary()
    let hasChartData = hasBacktestPayload(latestResult)

    if (!hasChartData && immediateResult.dates.length) {
      hasChartData = await applyBacktestResult(immediateResult)
    }

    if (!hasChartData) {
      chartError.value = '回测已完成，但前端没有拿到可绘制的收益趋势数据。'
      throw new Error(chartError.value)
    }

    const activeResult = hasBacktestPayload(backtestConfigResult.value) ? backtestConfigResult.value : backtestResultData.value
    persistLatestBacktest(activeResult)
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    if (autoTradeEnabled && activeResult?.dates?.includes(today)) {
      await sendAutoTradeData(activeResult.trades || {}, currentStrategy.value.strategyName || strategyName)
    }
  } catch (error) {
    console.error('startBacktest error:', error)
    chartError.value = chartError.value || error.response?.data?.error || error.message || '回测结果加载失败'
    ElMessage.error(error.response?.data?.message || error.message || '获取回测数据失败')
  }
}

const waitForPreparedReportData = async () => {
  const deadline = Date.now() + 45000
  let latestResult = backtestConfigResult.value

  while (Date.now() < deadline) {
    latestResult = await loadFullReportData()
    if (hasFullReportData(latestResult)) {
      return latestResult
    }
    await new Promise(resolve => setTimeout(resolve, 1500))
  }

  return latestResult
}

const openPreparedReport = async () => {
  const name = currentStrategy.value?.strategyName || strategyName
  if (!name) {
    ElMessage.error('请先选择策略')
    return
  }
  if (isPreparingReport.value) return

  if (!hasBacktestPayload(chartData.value)) {
    ElMessage.error('请先完成回测')
    return
  }

  isPreparingReport.value = true
  try {
    let preparedResult = chartData.value
    if (!hasFullReportData(preparedResult)) {
      preparedResult = await waitForPreparedReportData()
    }
    if (!hasFullReportData(preparedResult)) {
      ElMessage.error('报告模块数据尚未全部准备完成，请稍后再试')
      return
    }

    persistLatestBacktest(preparedResult)
    await router.push({
      path: '/strategy/report',
      query: {
        strategyName: name,
      },
    })
  } catch (error) {
    console.error('openPreparedReport error:', error)
    ElMessage.error(error.response?.data?.message || error.message || '报告准备失败')
  } finally {
    isPreparingReport.value = false
  }
}

watch(chartData, async value => {
  if (value?.dates?.length) {
    await nextTick()
    initChart()
  }
}, { deep: true })

onMounted(async () => {
  window.addEventListener('resize', resizeChart)
  try {
    const restored = restoreLatestBacktest()
    if (restored) {
      await nextTick()
      initChart()
    }
    await loadStrategySummary()
  } catch (error) {
    console.error('loadStrategyConfig error:', error)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.backtest-trigger {
  width: 100%;
}

.toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar button,
.start-backtest-btn {
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
}

.toolbar button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.content-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
}

.summary-panel,
.chart-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  padding: 20px;
}

.summary-panel h3,
.chart-panel h3 {
  margin: 0 0 16px;
}

.summary-table {
  width: 100%;
  border-collapse: collapse;
}

.summary-table th,
.summary-table td {
  border: 1px solid #e5e7eb;
  padding: 10px 12px;
  text-align: left;
}

.summary-table th {
  width: 120px;
  background: #f8fafc;
}

.chart-canvas {
  width: 100%;
  min-height: 420px;
}

.chart-error {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
}

@media (max-width: 960px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
