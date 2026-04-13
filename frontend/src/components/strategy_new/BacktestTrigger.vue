<template>
  <div class="backtest-trigger">
    <!-- 顶部横向导航栏 -->
    <div class="c-header c-header-horizontal">
      <ul class="c-header-nav-ul-horizontal">
        <li>
          <a
            :class="['nav-link', currentTab === '概览' ? 'active' : '']"
            @click="currentTab = '概览'"
            >概览</a>
        </li>
      </ul>
    </div>

    <!-- 页面内容容器 -->
    <div class="trigger-content">
      <!-- 概览页面 -->
      <div v-if="currentTab === '概览'" class="overview-container">
        <!-- 上层：左侧表格 + 右侧图表 -->
        <div class="flex mb-8">
          <!-- 左侧表格 -->
          <div class="bg-white p-4 rounded shadow flex-1 summary-container">
            <table class="summary-table">
              <thead>
                <tr>
                  <th>指标</th>
                  <th>值</th>
              </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in summaryData" :key="index">
                  <td>{{ item.label }}</td>
                  <td>{{ item.value }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 右侧图表区域 -->
          <div class="bg-white p-4 rounded shadow chart-container">
            <h3 class="text-lg font-semibold mb-4">📈 收益趋势图</h3>
            <div ref="chartRef" style="width: 1000px; height: 400px;" class="bg-gray-100 rounded"></div>
          </div>
        </div>
      </div>

      <!-- 收益分析页面（暂空） -->
      <div v-else-if="currentTab === '收益分析'" class="analysis-container">
        <p>收益分析页面暂未实现...</p>
      </div>

      <!-- 回撤分析页面（暂空） -->
      <div v-else-if="currentTab === '回撤分析'" class="analysis-container">
        <p>回撤分析页面暂未实现...</p>
      </div>
    </div>

     <div class="top-actions mb-4 flex justify-end">
    <button class="start-backtest-btn" @click="startBacktest">开始回测</button>
    <router-link :to="{
      path: '/strategy/report',
      query: {
        strategyName: props.params.strategy?.strategyName || strategyName,
        downloadPrompt: 'true'
      }
    }">
      <button>导出 PDF 报告</button>
    </router-link>
  </div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import axios from 'axios'
import { useRoute } from "vue-router"
import { ElMessage } from 'element-plus'

const route = useRoute()
const strategyName = route.params.id
const autoTradeEnabled = import.meta.env.VITE_ENABLE_AUTO_TRADE === 'true'
const tradeApiBaseUrl = (import.meta.env.VITE_TRADE_API_BASE_URL || '/trade-api').replace(/\/$/, '')

const currentTab = ref('概览')
const chartRef = ref(null)
let chartInstance = null

// 定义响应式数据
const props = defineProps({
  params: {
    type: Object,
    required: true,
    default: () => ({
      strategy: {},
      selector: {},
      factor: {}
    })
  }
})

// 本地响应式数据存储接口返回的配置
const strategyConfig = ref({
  capital: '',
  ratio: '',
  hold: '',
  benchmark: '',
  start_date: '',
  end_date: '',
  scope: ''
})

// 存储从后端获取的因子和选股器数据
const factorConfig = ref([])
const selectorConfig = ref([])

// 存储图表数据
const backtestResultData = ref({}) // getBackTrigger接口返回的图表数据
const backtestConfigResult = ref({}) // loadStrategyConfig接口返回的backtest_result数据

// 计算表格数据，优先使用从接口获取的配置数据
const summaryData = computed(() => {
  // 使用接口返回的数据，如果没有则使用props中的数据
  const s = {...props.params.strategy, ...strategyConfig.value}

  // 处理因子数据，优先使用props中的数据，如果没有则使用后端返回的数据
  let f = []
  if (props.params.factor?.received_data?.factors && props.params.factor.received_data.factors.length > 0) {
    f = props.params.factor.received_data.factors
  } else if (factorConfig.value && factorConfig.value.length > 0) {
    f = factorConfig.value
  }

  // 处理选股器数据，优先使用props中的数据，如果没有则使用后端返回的数据
  let sel = {}
  if (props.params.selector?.received_data?.conditions && props.params.selector.received_data.conditions.length > 0) {
    sel = props.params.selector.received_data.conditions[0] || {}
  } else if (selectorConfig.value && selectorConfig.value.length > 0) {
    sel = selectorConfig.value[0] || {}
  }

  // 构建因子字符串
  const factorStr = f.map(item => `${item.name || item.factor}${item.operator || ''}${item.value || ''}`).join('、')

  return [
    {label: '初始资金', value: `${s.capital}万元`},
    {label: '持股比例', value: `${s.ratio}%`},
    {label: '持股数目', value: `${s.hold}只`},
    {label: '收益基准', value: s.benchmark || '-'},
    {label: '时间范围', value: `${s.start_date} 至 ${s.end_date}`},
    {label: '选股范围', value: `板块(${s.scope})、风格(${s.scope})、行业(${s.scope})`},
    {label: '因子', value: factorStr || '-'},
    {label: '因子合成', value: sel.operator || '-'}
  ]
})

// 图表数据 - 优先使用getBackTrigger的数据，其次使用loadStrategyConfig中的backtest_result数据
const chartData = computed(() => {
  // 优先使用startBacktest获取的数据
  if (backtestResultData.value && Object.keys(backtestResultData.value).length > 0) {
    return backtestResultData.value
  }

  // 其次使用loadStrategyConfig接口返回的backtest_result数据
  if (backtestConfigResult.value && Object.keys(backtestConfigResult.value).length > 0) {
    return backtestConfigResult.value
  }

  // 如果都没有数据，返回空对象
  return {}
})

// 图表相关数据
const trade_date = computed(() => chartData.value.dates || [])
const income_base_price = computed(() => {
  if (chartData.value.benchmarkReturns) {
    return chartData.value.benchmarkReturns.map(r => r * 100)
  }
  return []
})
const backData = computed(() => {
  if (chartData.value.strategyReturns) {
    return chartData.value.strategyReturns.map(r => r * 100)
  }
  return []
})
const ShareHolding_stock = computed(() => chartData.value.ShareHolding_stock || {})
const TradeData = computed(() => chartData.value.trades || {})
const normalizeBacktestResult = (data = {}) => ({
  dates: data.dates || [],
  benchmarkReturns: data.benchmarkReturns || [],
  strategyReturns: data.strategyReturns || [],
  ShareHolding_stock: data.ShareHolding_stock || {},
  trades: data.trades || {}
})

const extractBacktestResult = (payload = {}) => {
  if (payload?.backtest_result) {
    return payload.backtest_result
  }
  if (payload?.backtestResult) {
    return payload.backtestResult
  }
  if (Array.isArray(payload?.dates) || Array.isArray(payload?.benchmarkReturns) || Array.isArray(payload?.strategyReturns)) {
    return payload
  }
  return {}
}

const applyBacktestResult = async (rawResult = {}) => {
  const normalized = normalizeBacktestResult(rawResult)
  backtestResultData.value = normalized
  props.params.trade_date = normalized.dates
  props.params.income_base_price = normalized.benchmarkReturns.map(r => r * 100)
  props.params.backData = normalized.strategyReturns.map(r => r * 100)
  props.params.ShareHolding_stock = normalized.ShareHolding_stock
  props.params.TradeData = normalized.trades

  if (normalized.dates.length > 0) {
    await refreshChart()
    return true
  }

  return false
}

const refreshChart = async () => {
  await nextTick()
  initChart()
}
const requestData = ref({
  incomeBase: '沪深300'
})

// 监听图表数据变化，自动更新图表
watch(chartData, async (newData) => {
  if (newData && Object.keys(newData).length > 0) {
    await refreshChart()
  }
}, { flush: 'post' })

// 加载策略配置
const loadStrategyConfig = async () => {
  try {
    // 如果没有策略名称，使用路由参数
    const name = props.params.strategy?.strategyName || strategyName

    if (!name) {
      console.warn('缺少策略名称，无法加载配置')
      return
    }

    const res = await axios.post('/api/strategy/loadStrategyConfig/', {
      strategyName: name
    }, {
      withCredentials: true
    })

    if (res.data.success) {
      // 更新策略配置数据
      strategyConfig.value = res.data.backtest_config

      // 同时更新params中的strategy数据
      Object.assign(props.params.strategy, res.data.backtest_config)

      // 解析并存储因子和选股器配置
      try {
        if (res.data.backtest_config.bottomfactor) {
          factorConfig.value = JSON.parse(res.data.backtest_config.bottomfactor.replace(/'/g, '"'))
        }
        if (res.data.backtest_config.optionfactor) {
          selectorConfig.value = JSON.parse(res.data.backtest_config.optionfactor.replace(/'/g, '"'))
        }
      } catch (e) {
        console.error('解析因子或选股器配置失败:', e)
      }

      // 存储backtest_result数据用于图表显示
      const loadedBacktestResult = extractBacktestResult(res.data)
      if (Object.keys(loadedBacktestResult).length > 0) {
        backtestConfigResult.value = normalizeBacktestResult(loadedBacktestResult)
        await refreshChart()
      }

      console.log('加载策略配置成功:', res.data)
    } else {
      console.error('加载策略失败:', res.data.message)
      alert('加载策略失败: ' + res.data.message)
    }
  } catch (err) {
    console.error('请求失败:', err)
    alert('加载策略失败，请检查网络或稍后重试')
  }
}

onMounted(() => {
  loadStrategyConfig()
})

// 开始回测方法
// 开始回测方法
const startBacktest = async () => {
  try {
    // 校验策略名称
    if (!props.params.strategy?.strategyName) {
      if (typeof ElMessage !== 'undefined') {
         ElMessage.error('请先选择策略')
      } else {
         alert('请先选择策略')
      }
      return
    }

    // 构造符合后端要求的 payload，确保结构完整 + 类型安全
    const selectorConditions = props.params.selector?.received_data?.conditions?.length
      ? props.params.selector.received_data.conditions
      : selectorConfig.value

    const factorItems = props.params.factor?.received_data?.factors?.length
      ? props.params.factor.received_data.factors
      : factorConfig.value

    const payload = {
      strategy: {
        strategyName: props.params.strategy?.strategyName || '',
        // 使用 ?? 0 防止 0 被视为 false
        capital: Number(props.params.strategy?.capital ?? 0),
        ratio: Number(props.params.strategy?.ratio ?? 100),
        hold: Number(props.params.strategy?.hold ?? 10),
        start_date: props.params.strategy?.start_date || '2025-12-01',
        end_date: props.params.strategy?.end_date || '2025-12-31',
      },
      selector: {
        received_data: {
          conditions: selectorConditions || []
        }
      },
      factor: {
        received_data: {
          factors: factorItems || []
        }
      }
    }

    // 发送 POST 请求，参数和图表数据都在同一个接口中处理
    const response = await axios.post('/api/strategy/getBackTrigger/', payload)

    console.log('开始回测，使用的策略:', payload.strategy)
    console.log('选股器:', payload.selector)
    console.log('因子配置:', payload.factor)

    const data = extractBacktestResult(response.data)

    // 存储回测结果数据
    let hasChartData = await applyBacktestResult(data)

    if (false) {
      await loadStrategyConfig()
      hasChartData = backtestConfigResult.value?.dates?.length > 0
      throw new Error('回测完成，但未返回可绘制的收益趋势数据')
    }

    // 更新 params，包含图表数据
    if (false) {
      throw new Error('鍥炴祴宸插畬鎴愶紝浣嗘湭鑾峰彇鍒板彲缁樺埗鐨勬敹鐩婅秼鍔挎暟鎹?')
    }

    if (!hasChartData) {
      await loadStrategyConfig()
      hasChartData = backtestConfigResult.value?.dates?.length > 0
    }

    if (!hasChartData) {
      throw new Error('Backtest finished but no chart data was returned.')
    }

    const activeResult = backtestResultData.value?.dates?.length ? backtestResultData.value : backtestConfigResult.value
    props.params.trade_date = activeResult?.dates || []
    props.params.income_base_price = (activeResult?.benchmarkReturns || []).map(r => r * 100)
    props.params.backData = (activeResult?.strategyReturns || []).map(r => r * 100)
    props.params.ShareHolding_stock = activeResult?.ShareHolding_stock || {}
    props.params.TradeData = activeResult?.trades || {}

    // 检查是否需要触发自动化交易（只有当回测包含当天日期时才触发）
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    console.log('今日回测结果:', today)
    if (autoTradeEnabled && activeResult?.dates?.includes(today)) {
      await sendAutoTradeData(activeResult.trades || {}, props.params.strategy.strategyName || strategyName)
    }


  } catch (error) {
    console.error('请求失败:', error)
    if (typeof ElMessage !== 'undefined') {
        ElMessage.error(error.response?.data?.message || '获取回测数据失败，请检查网络或重试')
    } else {
        alert(error.response?.data?.message || '获取回测数据失败，请检查网络或重试')
    }
  }
}

// 发送自动化交易数据的函数
const sendAutoTradeData = async (trades, strategyNo) => {
  try {
    if (!autoTradeEnabled) {
      return
    }

    // 获取今天的日期，格式为 YYYYMMDD
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')

    // 构造要发送的数据
    const tradeData = []

    // 只处理今天的交易数据
    if (trades[today]) {
      const todayTransactions = trades[today]

      // 遍历今天的交易
      for (const transaction of todayTransactions) {
        // 转换交易类型: 买入->buy, 卖出->sell
        let operate = ''
        if (transaction.trade_type === '买入') {
          operate = 'buy'
        } else if (transaction.trade_type === '卖出') {
          operate = 'sell'
        }

         // 处理股票代码，去除后缀（如.SZ, .SH）
        let stockCode = transaction.st_code || '';
        if (stockCode) {
          // 去除可能的后缀，如 .SZ, .SH 等
          stockCode = stockCode.split('.')[0];
        }

        // 只有在交易类型有效时才添加到发送数据中
        if (operate) {
          tradeData.push({
            strategy_no: strategyNo,  // 策略ID
            code: stockCode,  // 股票代码
            name: stockCode,  // 股票代码
            ct_amount: transaction.number_of_transactions,  // 交易数量
            operate: operate,  // 操作类型
            price: transaction.trade_price || 0   // 当天收盘价
          })
        }
      }
    }

    // 如果有今天的交易数据，则发送到自动化交易接口
    if (tradeData.length > 0) {
      await axios.post(`${tradeApiBaseUrl}/queue`, tradeData)
      console.log('今日自动化交易数据已发送:', tradeData)
    } else {
      console.log('今日没有交易数据需要发送')
    }
  } catch (error) {
    console.error('发送自动化交易数据失败:', error)
    // 不中断主流程，仅记录错误
  }
}

// 初始化图表
const initChart = () => {
  // 检查是否有数据可以绘制
  if (!trade_date.value || trade_date.value.length === 0) {
    console.log('没有图表数据可显示')
    return
  }

  if (!chartRef.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = echarts.init(chartRef.value)

  const option = {
    title: {
      text: '回测数据图'
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        let date = params[0].name
        let year = date.slice(0, 4)
        let month = date.slice(4, 6)
        let day = date.slice(6, 8)
        let content = `${year}-${month}-${day}<br/>`

        for (let i = 0; i < params.length; i++) {
          content += `${params[i].seriesName} : ${params[i].value}%<br/>`
        }

        updateTradeTable(date, ShareHolding_stock.value)
        updateStockTradeTable(date, TradeData.value)

        if (ShareHolding_stock.value && ShareHolding_stock.value[date]) {
          const stocks = ShareHolding_stock.value[date]
          content += `当日持仓: ${stocks.join(', ')}`
        } else {
          content += '当日持仓: 空仓'
        }

        return content
      }
    },
    legend: {
      data: [`${requestData.value.incomeBase}收益率`, '策略收益率']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
      backgroundColor: 'transparent'
    },
    xAxis: {
      type: 'category',
      data: trade_date.value
    },
    yAxis: {
      type: 'value',
      axisLabel: {formatter: '{value}%'}
    },
    series: [
      {
        name: `${requestData.value.incomeBase}收益率`,
        type: 'line',
        data: income_base_price.value,
        lineStyle: {color: 'red'},
        itemStyle: {color: 'red'}
      },
      {
        name: '策略收益率',
        type: 'line',
        data: backData.value,
        lineStyle: {color: 'blue'},
        itemStyle: {color: 'blue'}
      }
    ]
  }

  chartInstance.setOption(option)
  chartInstance.resize()
}

// 示例表格更新方法
const updateTradeTable = (date, holdings) => {
  console.log('更新持仓表格', date, holdings[date])
}

const updateStockTradeTable = (date, trades) => {
  console.log('更新交易明细', date, trades[date])
}
</script>

<style scoped>
/* 导航栏样式复用 strategy-new.vue */
.c-header-horizontal {
  background: #fbf8f8;
  color: #070000;
  padding: 0 20px;
}

.c-header-nav-ul-horizontal {
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
}

.c-header-nav-ul-horizontal li {
  margin-right: 20px;
}

.nav-link {
  color: #060000;
  text-decoration: none;
  font-size: 14px;
  padding: 6px 16px;
  border-radius: 12px;
  transition: background 0.3s, color 0.3s;
  display: inline-block;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
}

.nav-link.active {
  background: white;
  color: #00204a;
  font-weight: bold;
}

/* 内容区域 */
.trigger-content {
  background-color: #f9fafb;
}

.overview-container,
.analysis-container {
  padding: 20px;
  background-color: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.flex {
  display: flex;
  gap: 16px;
}

.summary-table {
  width: 100%;
  max-width: 400px;
  border-collapse: collapse;
}

.summary-table th,
.summary-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.summary-table th {
  background-color: #f2f2f2;
}
</style>
