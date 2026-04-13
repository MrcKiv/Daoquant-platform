<template>
  <div class="report-page">
    <div class="report-toolbar">
      <button class="toolbar-btn" :disabled="isGenerating || !reportReady" @click="handleGeneratePDF">
        {{ isGenerating ? '生成中...' : '下载 PDF' }}
      </button>
      <button class="toolbar-btn secondary" @click="refreshFromServer">刷新报告</button>
    </div>

    <div id="pdf-report-container" class="pdf-report-container">
      <header class="report-header">
        <div>
          <h1>策略回测报告</h1>
          <p>策略名称：{{ strategyName || currentStrategy.strategyName || '-' }}</p>
          <p>生成时间：{{ currentDate }}</p>
        </div>
      </header>

      <section class="section">
        <h2>回测设置</h2>
        <table class="summary-table">
          <tbody>
            <tr v-for="item in summaryRows" :key="item.label">
              <th>{{ item.label }}</th>
              <td>{{ item.value }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="hasBacktestData" class="section">
        <h2>收益趋势</h2>
        <div id="main-returns-chart" class="chart-block"></div>
      </section>

      <section v-if="hasBacktestData" class="section">
        <h2>回测指标</h2>
        <table class="summary-table metrics-table">
          <tbody>
            <tr>
              <th>最大回撤</th>
              <td>{{ formatPercentage(metrics.strategy.maxDrawdown) }}</td>
              <th>年化收益</th>
              <td>{{ formatPercentage(metrics.strategy.annualizedReturn) }}</td>
            </tr>
            <tr>
              <th>夏普比率</th>
              <td>{{ formatNumber(metrics.strategy.sharpeRatio) }}</td>
              <th>胜率</th>
              <td>{{ formatPercentage(metrics.strategy.winRate) }}</td>
            </tr>
            <tr>
              <th>索提诺比率</th>
              <td>{{ formatNumber(metrics.strategy.sortinoRatio) }}</td>
              <th>基准年化收益</th>
              <td>{{ formatPercentage(metrics.benchmark.annualizedReturn) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="hasBacktestData" class="section two-col">
        <div>
          <h2>日收益表现</h2>
          <div id="daily-return-chart" class="chart-block"></div>
        </div>
        <div>
          <h2>期间收益</h2>
          <div id="period-returns-chart" class="chart-block"></div>
        </div>
      </section>

      <section v-if="hasBacktestData" class="section two-col">
        <div>
          <h2>年度回报</h2>
          <div id="annual-returns-chart" class="chart-block"></div>
        </div>
        <div>
          <h2>持股数量时序</h2>
          <div id="holdings-timeline-chart" class="chart-block"></div>
        </div>
      </section>

      <section v-if="hasBacktestData" class="section two-col">
        <div>
          <h2>盈利归因前十</h2>
          <div id="stock-performance-chart" class="chart-block"></div>
        </div>
        <div>
          <h2>亏损归因前十</h2>
          <div id="stock-performance-loss-chart" class="chart-block"></div>
        </div>
      </section>

      <section v-if="hasBacktestData" class="section two-col">
        <div>
          <h2>行业配置时序</h2>
          <div id="industry-allocation-chart" class="chart-block"></div>
        </div>
        <div>
          <h2>持股行业分析</h2>
          <div id="industry-holdings-chart" class="chart-block"></div>
        </div>
      </section>

      <section v-if="hasBacktestData" class="section two-col">
        <div>
          <h2>期末市值占比</h2>
          <div id="end-period-market-value-chart" class="chart-block"></div>
        </div>
        <div>
          <h2>交易类型分析（买入）</h2>
          <div id="transaction-type-analysis-chart" class="chart-block"></div>
        </div>
      </section>

      <section v-if="hasBacktestData" class="section">
        <h2>交易类型分析（卖出）</h2>
        <div id="transaction-type-analysis-sell-chart" class="chart-block"></div>
      </section>

      <section v-if="hasBacktestData" class="section section-table">
        <h2>交易明细</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>股票</th>
              <th>方向</th>
              <th>数量</th>
              <th>价格</th>
              <th>金额</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(trade, index) in flattenedTrades" :key="`${trade.date}-${trade.code}-${index}`">
              <td>{{ formatDate(trade.date) }}</td>
              <td>{{ trade.code }}</td>
              <td>{{ trade.side }}</td>
              <td>{{ trade.quantity }}</td>
              <td>{{ trade.price }}</td>
              <td>{{ trade.amount }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="hasBacktestData && profitRows.length" class="section section-table">
        <h2>股票盈亏统计</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th>开始日期</th>
              <th>结束日期</th>
              <th>股票代码</th>
              <th>买入价</th>
              <th>卖出价</th>
              <th>成交手数</th>
              <th>盈亏资金</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in profitRows" :key="index">
              <td>{{ formatDate(row['持股开始日期']) }}</td>
              <td>{{ formatDate(row['持股终止日期']) }}</td>
              <td>{{ row['股票代码'] }}</td>
              <td>{{ formatNumber(row['买入价格']) }}</td>
              <td>{{ formatNumber(row['卖出价格']) }}</td>
              <td>{{ row['成交手数'] }}</td>
              <td :class="Number(row['盈亏资金']) >= 0 ? 'positive' : 'negative'">{{ formatNumber(row['盈亏资金']) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="!hasBacktestData" class="section empty-state">
        <h2>回测结果</h2>
        <p>当前没有可用的完整回测结果，请先重新运行回测。</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useGeneratePDF } from '@/stores/useGeneratePDF'

const route = useRoute()
const strategyName = route.query.strategyName
const showDownloadPrompt = route.query.downloadPrompt === 'true'
const currentDate = new Date().toLocaleString('zh-CN')
const reportReady = ref(false)

const strategyConfig = ref({})
const factorConfig = ref([])
const selectorConfig = ref([])
const backtestResult = ref(null)
const chartInstances = []
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

const getSnapshotKey = name => `daoquant:last-backtest:${name || 'unknown'}`

const parseMaybeJson = (value, fallback = []) => {
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

const extractBacktestResult = payload => {
  if (payload?.backtest_result) return payload.backtest_result
  if (payload?.backtestResult) return payload.backtestResult
  if (Array.isArray(payload?.dates) || Array.isArray(payload?.benchmarkReturns) || Array.isArray(payload?.strategyReturns)) {
    return payload
  }
  return null
}

const hasBacktestPayload = data => Array.isArray(data?.dates) && data.dates.length > 0

const hasFullReportData = data => {
  if (!hasBacktestPayload(data)) return false
  return REPORT_DATA_KEYS.every(key => Object.prototype.hasOwnProperty.call(data, key))
}

const restoreLatestBacktest = () => {
  if (!strategyName) return false
  const raw = sessionStorage.getItem(getSnapshotKey(strategyName))
  if (!raw) return false

  try {
    const snapshot = JSON.parse(raw)
    strategyConfig.value = snapshot.strategyConfig || {}
    factorConfig.value = snapshot.factorConfig || []
    selectorConfig.value = snapshot.selectorConfig || []
    backtestResult.value = normalizeBacktestResult(snapshot.backtestResult || {})
    return backtestResult.value?.dates?.length > 0
  } catch (error) {
    console.error('restoreLatestBacktest error:', error)
    return false
  }
}

const hasBacktestData = computed(() => Array.isArray(backtestResult.value?.dates) && backtestResult.value.dates.length > 0)
const currentStrategy = computed(() => strategyConfig.value || {})
const metrics = computed(() => backtestResult.value?.metrics || { strategy: {}, benchmark: {} })
const summaryRows = computed(() => {
  const factorStr = (factorConfig.value || [])
    .map(item => `${item.name || item.factor || ''}${item.operator || ''}${item.value ?? ''}`)
    .join('，')
  const selector = selectorConfig.value?.[0] || {}
  const s = currentStrategy.value
  return [
    { label: '策略名称', value: strategyName || s.strategyName || '-' },
    { label: '初始资金', value: s.capital || s.init_fund ? `${s.capital || s.init_fund}万元` : '-' },
    { label: '持股比例', value: s.ratio ? `${s.ratio}%` : '-' },
    { label: '持股数目', value: s.hold || s.max_hold_num || '-' },
    { label: '收益基准', value: s.benchmark || s.income_base || '-' },
    { label: '时间范围', value: s.start_date && s.end_date ? `${s.start_date} 至 ${s.end_date}` : '-' },
    { label: '因子', value: factorStr || '-' },
    { label: '策略选择', value: selector.operator || '-' },
  ]
})

const flattenedTrades = computed(() => {
  const items = []
  const trades = backtestResult.value?.trades || {}
  for (const [date, tradeList] of Object.entries(trades)) {
    for (const trade of tradeList) {
      items.push({
        date,
        code: trade.st_code || '',
        side: trade.trade_type || '',
        quantity: trade.number_of_transactions || 0,
        price: trade.trade_price || 0,
        amount: trade.turnover || (trade.trade_price || 0) * (trade.number_of_transactions || 0),
      })
    }
  }
  return items
})

const profitRows = computed(() => backtestResult.value?.calculate_stock_profit_loss || [])

const formatDate = value => {
  if (!value) return '-'
  const text = String(value)
  if (text.length === 8) {
    return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`
  }
  return text
}

const formatNumber = value => {
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  return number.toFixed(2)
}

const formatPercentage = value => {
  const number = Number(value)
  if (Number.isNaN(number)) return '-'
  return `${(number * 100).toFixed(2)}%`
}

const createChart = (id, option) => {
  const container = document.getElementById(id)
  if (!container) return null

  const chart = echarts.init(container)
  chart.setOption(option, true)
  chartInstances.push(chart)
  return chart
}

const disposeCharts = () => {
  while (chartInstances.length) {
    const chart = chartInstances.pop()
    if (chart && !chart.isDisposed()) {
      chart.dispose()
    }
  }
}

const baseTitle = text => ({
  text,
  left: 'center',
  top: 10,
  textStyle: { fontSize: 18, fontWeight: 'normal', color: '#333' },
})

const initMainChart = () => {
  createChart('main-returns-chart', {
    title: baseTitle('收益趋势图'),
    tooltip: { trigger: 'axis' },
    legend: { data: [currentStrategy.value?.benchmark || 'Benchmark', 'Strategy'], bottom: 10 },
    grid: { left: '3%', right: '4%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: backtestResult.value.dates },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: currentStrategy.value?.benchmark || 'Benchmark',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: backtestResult.value.benchmarkReturns.map(v => Number(v) * 100),
      },
      {
        name: 'Strategy',
        type: 'line',
        smooth: true,
        showSymbol: false,
        data: backtestResult.value.strategyReturns.map(v => Number(v) * 100),
      },
    ],
  })
}

const initDailyReturnChart = () => {
  const data = backtestResult.value.daily_returns || []
  createChart('daily-return-chart', {
    title: baseTitle('日收益表现'),
    tooltip: { trigger: 'axis' },
    legend: { data: ['策略', '基准'], bottom: 10 },
    grid: { left: '5%', right: '5%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: data.map(item => item['日期']), axisLabel: { rotate: 45 } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '策略', type: 'bar', data: data.map(item => Number(item['日收益率']) * 100) },
      { name: '基准', type: 'bar', data: data.map(item => Number(item['日收益率（基准）']) * 100) },
    ],
  })
}

const initPeriodReturnChart = () => {
  const data = backtestResult.value.period_returns || []
  createChart('period-returns-chart', {
    title: baseTitle('期间收益'),
    tooltip: { trigger: 'axis' },
    legend: { data: ['策略', '基准'], bottom: 10 },
    grid: { left: '5%', right: '5%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: data.map(item => item.period) },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '策略', type: 'bar', data: data.map(item => item.strategy_return == null ? null : Number(item.strategy_return) * 100) },
      { name: '基准', type: 'bar', data: data.map(item => item.benchmark_return == null ? null : Number(item.benchmark_return) * 100) },
    ],
  })
}

const initAnnualReturnChart = () => {
  const data = backtestResult.value.annual_returns || []
  createChart('annual-returns-chart', {
    title: baseTitle('年度回报'),
    tooltip: { trigger: 'axis' },
    legend: { data: ['策略', '基准'], bottom: 10 },
    grid: { left: '5%', right: '5%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: data.map(item => item.year || item.period || 'YTD') },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '策略', type: 'bar', data: data.map(item => Number(item.strategy_return || 0) * 100) },
      { name: '基准', type: 'bar', data: data.map(item => Number(item.benchmark_return || 0) * 100) },
    ],
  })
}

const initStockPerformanceChart = () => {
  const data = backtestResult.value.stock_performance_attribution_range || backtestResult.value.stock_performance_attribution || []
  createChart('stock-performance-chart', {
    title: baseTitle('盈利归因前十'),
    tooltip: { trigger: 'axis' },
    grid: { left: '20%', right: '8%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.map(item => item.stock_name) },
    series: [{ type: 'bar', data: data.map(item => Number(item.profit_amount_wan || 0)) }],
  })
}

const initStockPerformanceLossChart = () => {
  const data = backtestResult.value.stock_performance_attribution_loss_range || []
  createChart('stock-performance-loss-chart', {
    title: baseTitle('亏损归因前十'),
    tooltip: { trigger: 'axis' },
    grid: { left: '20%', right: '8%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.map(item => item.stock_name) },
    series: [{ type: 'bar', data: data.map(item => Number(item.loss_amount_wan || 0)) }],
  })
}

const initIndustryAllocationChart = () => {
  const data = backtestResult.value.industry_allocation_timeline || {}
  createChart('industry-allocation-chart', {
    title: baseTitle('行业配置时序'),
    tooltip: { trigger: 'axis' },
    legend: { data: (data.series || []).map(item => item.name), bottom: 10, type: 'scroll' },
    grid: { left: '5%', right: '5%', bottom: '20%', containLabel: true },
    xAxis: { type: 'category', data: data.dates || [] },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: (data.series || []).map(item => ({ ...item, smooth: true })),
  })
}

const initHoldingsTimelineChart = () => {
  const data = backtestResult.value.holdings_timeline || {}
  createChart('holdings-timeline-chart', {
    title: baseTitle('持股数量时序'),
    tooltip: { trigger: 'axis' },
    legend: { data: ['持股数量', '持股数量（剔除新股）'], bottom: 10 },
    grid: { left: '5%', right: '5%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: data.dates || [] },
    yAxis: { type: 'value' },
    series: [
      { name: '持股数量', type: 'line', smooth: true, data: data.total_holdings || [] },
      { name: '持股数量（剔除新股）', type: 'line', smooth: true, data: data.filtered_holdings || [] },
    ],
  })
}

const initIndustryHoldingsChart = () => {
  const data = backtestResult.value.industry_holdings_analysis || {}
  createChart('industry-holdings-chart', {
    title: baseTitle('持股行业分析'),
    tooltip: { trigger: 'axis' },
    grid: { left: '20%', right: '8%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: data.industries || [] },
    series: [{ type: 'bar', data: data.percentages || [] }],
  })
}

const initEndPeriodMarketValueChart = () => {
  const data = backtestResult.value.end_period_market_value_proportion || {}
  createChart('end-period-market-value-chart', {
    title: baseTitle('期末市值占比'),
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: (data.industries || []).map((industry, index) => ({
        name: industry,
        value: (data.percentages || [])[index] || 0,
      })),
    }],
  })
}

const initTransactionTypeAnalysisChart = () => {
  const data = backtestResult.value.transaction_type_analysis || {}
  const periods = Object.keys(data)
  createChart('transaction-type-analysis-chart', {
    title: baseTitle('交易类型分析（买入）'),
    tooltip: { trigger: 'axis' },
    legend: { data: ['趋势', '反转'], bottom: 10 },
    grid: { left: '5%', right: '5%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '趋势', type: 'bar', data: periods.map(period => Number(data[period]?.trend_percentage || 0)) },
      { name: '反转', type: 'bar', data: periods.map(period => Number(data[period]?.reversal_percentage || 0)) },
    ],
  })
}

const initTransactionTypeAnalysisSellChart = () => {
  const data = backtestResult.value.transaction_type_analysis_sell || {}
  const periods = Object.keys(data)
  createChart('transaction-type-analysis-sell-chart', {
    title: baseTitle('交易类型分析（卖出）'),
    tooltip: { trigger: 'axis' },
    legend: { data: ['趋势', '反转'], bottom: 10 },
    grid: { left: '5%', right: '5%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '趋势', type: 'bar', data: periods.map(period => Number(data[period]?.trend_percentage || 0)) },
      { name: '反转', type: 'bar', data: periods.map(period => Number(data[period]?.reversal_percentage || 0)) },
    ],
  })
}

const renderAllCharts = async () => {
  disposeCharts()
  if (!hasBacktestData.value) {
    reportReady.value = false
    return
  }

  await nextTick()
  initMainChart()
  initDailyReturnChart()
  initPeriodReturnChart()
  initAnnualReturnChart()
  initStockPerformanceChart()
  initStockPerformanceLossChart()
  initIndustryAllocationChart()
  initHoldingsTimelineChart()
  initIndustryHoldingsChart()
  initEndPeriodMarketValueChart()
  initTransactionTypeAnalysisChart()
  initTransactionTypeAnalysisSellChart()
  await new Promise(resolve => setTimeout(resolve, 800))
  chartInstances.forEach(chart => chart.resize())
  reportReady.value = true
}

const loadStrategyConfig = async () => {
  const res = await axios.post('/api/strategy/loadStrategyConfig/', { strategyName }, { withCredentials: true })
  if (!res.data?.success) {
    const errorMessage = res.data?.message || res.data?.error || 'Unknown error'
    throw new Error(errorMessage)
  }

  strategyConfig.value = res.data.backtest_config || res.data.received_data || {}
  factorConfig.value = parseMaybeJson(res.data.backtest_config?.bottomfactor, [])
  selectorConfig.value = parseMaybeJson(res.data.backtest_config?.optionfactor, [])

  const loadedResult = extractBacktestResult(res.data)
  if (loadedResult && loadedResult.dates?.length) {
    backtestResult.value = normalizeBacktestResult(loadedResult)
  }
}

const { generatePDF, isGenerating } = useGeneratePDF({
  containerId: 'pdf-report-container',
  filename: `strategy-report-${strategyName || 'report'}`,
  format: 'a4',
  orientation: 'portrait',
  margin: [10, 5, 10, 5],
  scale: 1,
  useNativePrint: true,
})

const handleGeneratePDF = async () => {
  if (!hasBacktestData.value || !reportReady.value) return
  await nextTick()
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
  await new Promise(resolve => setTimeout(resolve, 1200))
  chartInstances.forEach(chart => chart.resize())
  await generatePDF()
}

const refreshFromServer = async () => {
  reportReady.value = false
  await loadStrategyConfig()
  await renderAllCharts()
}

onMounted(async () => {
  try {
    const restored = restoreLatestBacktest()
    if (!restored || !hasFullReportData(backtestResult.value)) {
      await loadStrategyConfig()
    }
    await renderAllCharts()
    if (showDownloadPrompt && hasBacktestData.value) {
      await handleGeneratePDF()
    }
  } catch (error) {
    console.error('BacktestReportFixed load error:', error)
    reportReady.value = false
  }
})

onUnmounted(() => {
  disposeCharts()
})
</script>

<style scoped>
.report-page {
  background: #f5f7fb;
  min-height: 100vh;
  padding: 16px;
}

.report-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 16px;
}

.toolbar-btn {
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  background: #1d4ed8;
  color: #fff;
  cursor: pointer;
}

.toolbar-btn.secondary {
  background: #475569;
}

.toolbar-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pdf-report-container {
  width: 960px;
  margin: 0 auto;
  background: #fff;
  color: #111827;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 16px;
  margin-bottom: 24px;
}

.report-header h1 {
  margin: 0 0 8px;
}

.section {
  margin-bottom: 28px;
  page-break-inside: avoid;
}

.section h2 {
  margin: 0 0 16px;
  font-size: 22px;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.summary-table,
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.summary-table th,
.summary-table td,
.data-table th,
.data-table td {
  border: 1px solid #e5e7eb;
  padding: 10px 12px;
  text-align: left;
}

.summary-table th,
.data-table th {
  background: #f8fafc;
}

.data-table thead {
  display: table-header-group;
}

.data-table tr,
.summary-table tr {
  break-inside: avoid;
  page-break-inside: avoid;
}

.chart-block {
  width: 100%;
  min-height: 380px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

.metrics-table th {
  width: 18%;
}

.positive {
  color: #dc2626;
}

.negative {
  color: #059669;
}

.empty-state {
  text-align: center;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  padding: 40px 20px;
}

@media (max-width: 1024px) {
  .pdf-report-container {
    width: 100%;
  }

  .two-col {
    grid-template-columns: 1fr;
  }
}

@page {
  size: A4;
  margin: 10mm;
}

@media print {
  .report-page {
    background: #fff;
    padding: 0;
  }

  .report-toolbar {
    display: none !important;
  }

  .pdf-report-container {
    width: 100%;
    margin: 0;
    padding: 0;
    border-radius: 0;
    box-shadow: none;
  }

  .section,
  .chart-block,
  .data-table,
  .summary-table {
    break-inside: avoid;
    page-break-inside: avoid;
  }

  .section-table {
    break-inside: auto;
    page-break-inside: auto;
  }

  .section-table > h2 {
    break-after: avoid-page;
    page-break-after: avoid;
    margin-bottom: 8px;
  }

  .section-table > h2 + .data-table {
    break-before: avoid-page;
    page-break-before: avoid;
  }

  .two-col {
    grid-template-columns: 1fr 1fr;
  }

  * {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
</style>
