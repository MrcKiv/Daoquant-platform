<template>
  <div id="pdf-report-container" class="pdf-report-container">
    <!-- 页眉 -->
    <div class="header running-header">
      <div class="header-content">
        <span>山西量道科技有限公司</span>
        <span class="page-number"></span>
      </div>
    </div>

    <!-- 封面页 -->
    <div class="cover-page">
      <!-- Logo 和标题 -->
      <div class="header" style="text-align: center; margin-bottom: 30px;">
        <div style="display: flex; justify-content: flex-end; margin-bottom: 20px;">
          <!-- 替换 logo-placeholder 为实际图片 -->
          <img src="/images/logo/logo_mql.jpg" alt="Logo" style="width: 100px; height: 100px; border: 1px dashed #999;">
        </div>
        <h1 style="font-size: 28px; font-weight: bold; color: #000; margin: 60px 0 30px;">山西量道科技有限公司</h1>
        <h2 style="font-size: 24px; font-weight: bold; color: #000; margin: 20px 0;">策略详情</h2>
        <div class="report-info">
          <p><strong>策略名称：</strong>{{ strategyName || '未命名策略' }}</p>
          <p><strong>生成日期：</strong>{{ currentDate }}</p>
        </div>
      </div>
    </div>

    <div class="page-break"></div>

    <!-- 主要内容区域 -->
    <div class="main-content">
            <!-- 当天买卖股情况 -->
      <div class="content-section">
        <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px; margin-top: 30px;">当日买卖股情况</h3>
        <div class="trades-table" style="margin: 15px 0;">
          <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; font-size: 12px;">
            <thead>
              <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px; border: 1px solid #ddd;">交易日期</th>
                <th style="padding: 8px; border: 1px solid #ddd;">股票代码</th>
                <th style="padding: 8px; border: 1px solid #ddd;">买卖标识</th>
                <th style="padding: 8px; border: 1px solid #ddd;">数量(手)</th>
                <th style="padding: 8px; border: 1px solid #ddd;">每股单价（元)</th>
                <th style="padding: 8px; border: 1px solid #ddd;">交易资金（元）</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(trade, index) in latestTrades" :key="index">
                <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.date }}</td>
                <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.code }}</td>
                <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.side }}</td>
                <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.quantity }}</td>
                <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.price }}</td>
                <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.amount }}</td>
              </tr>
              <tr v-if="latestTrades.length === 0">
                <td colspan="6" style="padding: 6px; border: 1px solid #ddd; text-align: center;">暂无交易记录</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <!-- 回测指标和回测结果图并排显示 -->
      <div class="content-row">
        <!-- 左侧：回测指标和值 -->
        <div class="content-left">
          <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px;">回测指标和值</h3>
          <div class="summary-table" style="margin: 15px 0;">
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">
              <thead>
                <tr style="background-color: #f2f2f2;">
                  <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">指标</th>
                  <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">值</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, i) in summary" :key="i">
                  <td style="padding: 8px; border: 1px solid #ddd;">{{ item.label }}</td>
                  <td style="padding: 8px; border: 1px solid #ddd;">{{ item.value }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>



        <!-- 右侧：回测结果图 -->
        <div class="content-right">
          <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px;">回测结果图</h3>
          <div id="pdf-chart-container" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>
        </div>
      </div>



      <!-- 买卖股分析 -->
      <div class="content-section">
        <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px;">买卖股分析</h3>
        <p style="margin: 10px 0; line-height: 1.6;">
          本策略在{{ formatDate(tradeStartDate) }} 至 {{ formatDate(tradeEndDate) }}回测期间共进行 {{ calculateStockProfitLoss.length }} 笔交易。<br>
          其中<span :style="{ color: profitableTradesCount > 0 ? 'red' : 'green' }">
            盈利交易 {{ profitableTradesCount }} 笔，盈利共计 {{ formatCurrency(totalProfit) }} 元。
          </span>
          <span style="color: green"><br>
            亏损交易 {{ lossTradesCount }} 笔，亏损共计 {{ formatCurrency(Math.abs(totalLoss)) }} 元。
          </span>

          <span :style="{ color: (totalProfit + totalLoss) >= 0 ? 'red' : 'green' }"><br>
            最终{{ (totalProfit + totalLoss) >= 0 ? '盈利' : '亏损' }} {{ formatCurrency(Math.abs(totalProfit + totalLoss)) }} 元
          </span>。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
// ... 保持原有脚本代码不变 ...
import * as echarts from 'echarts'
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useGeneratePDF } from '@/stores/useGeneratePDF'

const route = useRoute()
const strategyName = route.query.strategyName
const showDownloadPrompt = route.query.downloadPrompt === 'true'

// 当前日期
const currentDate = new Date().toLocaleDateString('zh-CN')

// 数据存储
const strategyConfig = ref({})
const backtestResult = ref({})
const factorConfig = ref([])
const selectorConfig = ref([])
const metrics = ref({})

// 从后端获取的真实交易数据
const realTrades = computed(() => {
  const trades = []
  if (backtestResult.value.trades) {
    // 遍历交易数据，按日期组织
    for (const [date, tradeList] of Object.entries(backtestResult.value.trades)) {
      tradeList.forEach(trade => {
        trades.push({
          date: date,
          code: trade.st_code || '',
          side: trade.trade_type || '',
          quantity: trade.number_of_transactions || 0,
          price: trade.trade_price || 0,
          amount: trade.turnover || (trade.trade_price * trade.number_of_transactions) || 0
        })
      })
    }
  }
  return trades
})

// 获取最新的交易记录（当天或最后一天）
const latestTrades = computed(() => {
  if (realTrades.value.length > 0) {
    // 获取最后一天的交易
    const lastTradeDate = realTrades.value[realTrades.value.length - 1].date;
    return realTrades.value.filter(trade => trade.date === lastTradeDate);
  }
  return [];
})

const sampleTrades = computed(() => {
  return realTrades.value.length > 0 ? realTrades.value : [
    { date: '2024-01-15', code: '000001', name: '平安银行', side: '买入', quantity: 100, price: 12.5, amount: 125000 },
    { date: '2024-02-20', code: '000002', name: '万科A', side: '卖出', quantity: 50, price: 25.8, amount: 129000 }
  ]
})

const profitableTradesCount = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss.filter(item => item['盈亏资金'] > 0).length;
  }
  return 0;
});

const lossTradesCount = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss.filter(item => item['盈亏资金'] < 0).length;
  }
  return 0;
});

const totalProfit = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss
      .filter(item => item['盈亏资金'] > 0)
      .reduce((sum, item) => sum + item['盈亏资金'], 0);
  }
  return 0;
});

const totalLoss = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss
      .filter(item => item['盈亏资金'] < 0)
      .reduce((sum, item) => sum + item['盈亏资金'], 0);
  }
  return 0;
});

// 添加货币格式化函数
const formatCurrency = (value) => {
  return value.toFixed(2);
};

const tradeStartDate = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss && backtestResult.value.calculate_stock_profit_loss.length > 0) {
    // 获取最早的持股开始日期
    const dates = backtestResult.value.calculate_stock_profit_loss.map(item => item['持股开始日期']);
    return Math.min(...dates.map(date => parseInt(date)));
  }
  return null;
});

const tradeEndDate = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss && backtestResult.value.calculate_stock_profit_loss.length > 0) {
    // 获取最晚的持股终止日期
    const dates = backtestResult.value.calculate_stock_profit_loss.map(item => item['持股终止日期']);
    return Math.max(...dates.map(date => parseInt(date)));
  }
  return null;
});

const calculateStockProfitLoss = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss
  }
  return []
})

// 添加日期格式化函数
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  // 将 YYYYMMDD 格式转换为 YYYY-MM-DD
  const dateStrFormatted = dateStr.toString()
  if (dateStrFormatted.length === 8) {
    const year = dateStrFormatted.substring(0, 4)
    const month = dateStrFormatted.substring(4, 6)
    const day = dateStrFormatted.substring(6, 8)
    return `${year}-${month}-${day}`
  }
  return dateStr
}

const profitableStocks = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    // 筛选出盈亏资金为正数的股票（盈利股票）
    return backtestResult.value.calculate_stock_profit_loss.filter(item => item['盈亏资金'] > 0);
  }
  return [];
});

// 表格数据
const summary = computed(() => {
  const s = strategyConfig.value || {}
  const f = factorConfig.value || []
  const sel = selectorConfig.value?.[0] || {}

  const factorStr = f.map(item => `${item.name || item.factor || ''}${item.operator || ''}${item.value || ''}`).join('、')

  return [
    { label: '初始资金', value: `${s.capital || s.init_fund}万元` },
    { label: '持股比例', value: `${s.ratio || 100}%` },
    { label: '持股数目', value: `${s.hold || s.max_hold_num}只` },
    { label: '收益基准', value: s.benchmark || s.income_base || '-' },
    { label: '时间范围', value: `${s.start_date} 至 ${s.end_date}` },
    { label: '选股范围', value: `板块(${s.scope || '全部'})、风格(${s.scope || '全部'})、行业(${s.scope || '全部'})` },
    { label: '因子', value: factorStr || '-' },
    { label: '因子合成', value: sel.operator || '-' }
  ]
})

// 图表数据
const trade_date = computed(() => backtestResult.value.dates || [])
const income_base_price = computed(() => {
  if (backtestResult.value.benchmarkReturns) {
    return backtestResult.value.benchmarkReturns.map(r => r * 100)
  }
  return []
})
const backData = computed(() => {
  if (backtestResult.value.strategyReturns) {
    return backtestResult.value.strategyReturns.map(r => r * 100)
  }
  return []
})
const ShareHolding_stock = computed(() => backtestResult.value.ShareHolding_stock || {})
const TradeData = computed(() => backtestResult.value.trades || {})

// 计算方法
const getStrategyTags = () => {
  const s = strategyConfig.value || {}
  const metricsData = metrics.value?.strategy || {}

  // 根据策略参数生成标签
  const tags = []
  if ((s.ratio || 100) > 50) tags.push('集中型')
  else tags.push('分散型')

  if (metricsData.annualizedReturn > 0.3) tags.push('高收益型')
  else if (metricsData.annualizedReturn > 0.1) tags.push('稳健型')
  else tags.push('保守型')

  if ((metricsData.maxDrawdown || 0) > -0.2) tags.push('低风险型')
  else tags.push('高风险型')

  return tags.join('、') || '未分类'
}

const getStockCount = () => {
  // 从持仓数据中计算股票数量
  const holdings = ShareHolding_stock.value
  if (Object.keys(holdings).length > 0) {
    const allStocks = new Set()
    Object.values(holdings).forEach(stocks => {
      stocks.forEach(stock => allStocks.add(stock))
    })
    return allStocks.size
  }
  return 0
}

const getStockList = () => {
  // 从持仓数据中获取股票列表
  const holdings = ShareHolding_stock.value
  if (Object.keys(holdings).length > 0) {
    const allStocks = new Set()
    Object.values(holdings).forEach(stocks => {
      stocks.forEach(stock => allStocks.add(stock))
    })
    return Array.from(allStocks).join(', ')
  }
  return '暂无股票数据'
}

const formatPercentage = (value) => {
  return (value * 100).toFixed(2)
}

// 加载策略配置
const loadStrategyConfig = async () => {
  try {
    const res = await axios.post('/api/strategy/loadStrategyConfig/', {
      strategyName: strategyName
    }, {
      withCredentials: true
    })
    console.log('success:',res.data.success)
    console.log('加载策略配置:', res.data)
    if (res.data.success) {
      // 更新策略配置数据
      strategyConfig.value = res.data.backtest_config || res.data.received_data || {}

      // 解析并存储因子和选股器配置
      try {
        if (res.data.backtest_config?.bottomfactor) {
          factorConfig.value = JSON.parse(res.data.backtest_config.bottomfactor.replace(/'/g, '"'))
        }
        if (res.data.backtest_config?.optionfactor) {
          selectorConfig.value = JSON.parse(res.data.backtest_config.optionfactor.replace(/'/g, '"'))
        }
      } catch (e) {
        console.error('解析因子或选股器配置失败:', e)
      }

      // 存储backtest_result数据用于图表显示
      if (res.data.backtest_result && Object.keys(res.data.backtest_result).length > 0) {
        backtestResult.value = res.data.backtest_result
        metrics.value = res.data.backtest_result.metrics || {}
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

// 初始化图表
const initChart = () => {
  const container = document.getElementById('pdf-chart-container')
  if (!container) return

  const chart = echarts.init(container)

  const option = {
    title: {
      text: '回测数据图',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
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
      data: ['沪深300收益率', '策略收益率']
    },
    grid: {
      left: '8%',
      right: '4%',
      bottom: '15%',
      containLabel: true,
      backgroundColor: 'transparent'
    },
    xAxis: {
      type: 'category',
      data: trade_date.value,
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}%',
        fontSize: 10
      }
    },
    series: [
      {
        name: '沪深300收益率',
        type: 'line',
        data: income_base_price.value,
        lineStyle: { color: 'red' },
        itemStyle: { color: 'red' },
        smooth: true
      },
      {
        name: '策略收益率',
        type: 'line',
        data: backData.value,
        lineStyle: { color: 'blue' },
        itemStyle: { color: 'blue' },
        smooth: true
      }
    ]
  }

  chart.setOption(option)
}

const initDailyReturnChart = () => {
  const chartDom = document.getElementById('daily-return-chart')
  const myChart = echarts.init(chartDom)

  // 从 backtestResult.value.daily_returns 获取数据
  const dailyReturnsData = backtestResult.value.daily_returns || []

  // 转换数据格式
  const dailyReturns = dailyReturnsData.map(item => {
    const date = new Date(item['日期'])
    const timestamp = date.getTime()
    const value = item['日收益率']
    return [timestamp, value]
  })

  const benchmarkReturns = dailyReturnsData.map(item => {
    const date = new Date(item['日期'])
    const timestamp = date.getTime()
    const value = item['日收益率（基准）']
    return [timestamp, value]
  })

  const option = {
    title: {
      text: '日收益率',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        let date = new Date(params[0].name).toLocaleDateString()
        let content = `${date}<br/>`

        params.forEach(param => {
          content += `${param.seriesName}: ${param.value * 100}%<br/>`
        })

        return content
      }
    },
    legend: {
      data: ['日收益率', '日收益率（基准）']
    },
    xAxis: {
      type: 'time',
      axisLabel: {
        formatter: function (value) {
          return echarts.format.formatTime('yyyy-MM-dd', value)
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: '日收益率',
        type: 'line',
        data: dailyReturns,
        itemStyle: {
          color: 'red'
        }
      },
      {
        name: '日收益率（基准）',
        type: 'line',
        data: benchmarkReturns,
        itemStyle: {
          color: 'blue'
        }
      }
    ]
  }

  myChart.setOption(option)
}

// 初始化 useGeneratePDF
const {
  generatePDF,
  isGenerating
} = useGeneratePDF({
  containerId: 'pdf-report-container',
  filename: '策略回测报告',
  format: 'a4',
  orientation: 'portrait',
  margin: [10, 5, 10, 5],
  scale: 2,
})

// 显示下载确认弹窗
const showDownloadConfirmation = () => {
  if (showDownloadPrompt) {
    setTimeout(() => {
      if (confirm('报告已生成完成，是否立即下载PDF文件？')) {
        generatePDF()
      }
    }, 1000) // 延迟1秒显示，确保页面渲染完成
  }
}

onMounted(async () => {
  // 加载策略配置和回测结果
  await loadStrategyConfig()

  // 初始化图表
  initChart()
  // initDailyReturnChart()

  // 延迟确保图表渲染完成
  await new Promise(resolve => setTimeout(resolve, 500))

  // // 显示下载确认弹窗
  // showDownloadConfirmation()
})
</script>

<style scoped>
/* 页面容器样式 */
.pdf-report-container {
  width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  background: white;
  color: black;
  position: relative;
}

/* 页眉样式 */
.running-header {
  position: running(header);
  width: 100%;
  border-bottom: 1px solid #ccc;
  padding: 10px 0;
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #666;
}

/* 封面页样式 */
.cover-page {
  text-align: center;
  padding: 40px 0;
}

.logo-placeholder {
  width: 100px;
  height: 100px;
  border: 1px dashed #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #999;
}

.report-info {
  margin-top: 80px;
  text-align: left;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.report-info p {
  margin: 10px 0;
  font-size: 16px;
}

/* 主要内容区域 */
.main-content {
  margin-top: 20px;
}

.content-row {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
}

.content-left {
  flex: 0 0 30%; /* 左侧区域占 40% */
}

.content-right {
  flex: 0 0 70%; /* 右侧区域占 60% */
}

.content-section {
  margin-bottom: 30px;
}

/* 表格样式 */
.summary-table table,
.trades-table table {
  width: 100%;
  border-collapse: collapse;
}

.summary-table th,
.summary-table td,
.trades-table th,
.trades-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.summary-table th,
.trades-table th {
  background-color: #f2f2f2;
  font-weight: bold;
}

/* 分页符 */
.page-break {
  page-break-after: always;
  margin: 20px 0;
}

/* PDF打印样式 */
@page {
  @top-center {
    content: element(header);
  }
  margin: 80px 20px 80px 20px;
}

@media print {
  .pdf-report-container {
    width: 100%;
    padding: 0;
  }

  .page-break {
    page-break-after: always;
    margin: 0;
  }

  .running-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 60px;
  }

  .content-row {
    display: block;
  }

  .content-left,
  .content-right {
    width: 100%;
    margin-bottom: 20px;
  }
}
</style>
