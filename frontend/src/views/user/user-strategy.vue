<!-- src/views/user/user-strategy.vue -->
<template>
  <FixedNavbar />
  <div class="user-strategy-container">
    <h2 class="page-title">我的策略</h2>
    <div class="card-container my-strategies">
      <div
        v-for="(item, index) in myStrategies"
        :key="index"
        class="strategy-card"
        @click="goToStrategyDetail(item)"
        style="cursor: pointer;"
      >
        <!-- 使用回测数据图替换原来的图片 -->
        <div class="chart-container" v-if="item.chartData && item.chartData.dates && item.chartData.dates.length > 0">
          <div :id="`chart-${item.id}`" class="strategy-chart"></div>
        </div>
        <div class="chart-container" v-else>
          <div class="no-chart">暂无图表数据</div>
        </div>

        <h3 class="strategy-title">{{ item.strategyName }}</h3>

        <!-- 双列显示的策略信息 -->
        <div class="strategy-info-grid">
          <div class="info-item">
            <span class="info-label">年化收益</span>
            <span class="info-value highlight">{{ item.annualReturn }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">最大回撤</span>
            <span class="info-value">{{ item.maxDrawdown }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">初始资金</span>
            <span class="info-value">{{ item.capital }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">订阅人数</span>
            <span class="info-value">{{ item.userCount || 0 }}人</span>
          </div>
        </div>
      </div>
    </div>

    <h2 class="page-title">订阅策略</h2>
    <div class="card-container subscribed-strategies">
      <div
        v-for="(item, index) in subscribedStrategies"
        :key="index"
        class="strategy-card"
        @click="goToStrategyDetail(item)"
        style="cursor: pointer;"
      >
        <!-- 使用回测数据图替换原来的图片 -->
        <div class="chart-container" v-if="item.chartData && item.chartData.dates && item.chartData.dates.length > 0">
          <div :id="`chart-${item.id}`" class="strategy-chart"></div>
        </div>
        <div class="chart-container" v-else>
          <div class="no-chart">暂无图表数据</div>
        </div>

        <h3 class="strategy-title">{{ item.strategyName }}</h3>

        <!-- 双列显示的策略信息 -->
        <div class="strategy-info-grid">
          <div class="info-item">
            <span class="info-label">年化收益</span>
            <span class="info-value highlight">{{ item.annualReturn }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">最大回撤</span>
            <span class="info-value">{{ item.maxDrawdown }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">初始资金</span>
            <span class="info-value">{{ item.capital }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">订阅人数</span>
            <span class="info-value">{{ item.userCount || 0 }}人</span>
          </div>
        </div>

        <div class="strategy-footer">
          <button
            class="subscribe-btn"
            @click.stop="subscribeStrategy(item)"
            :disabled="item.isSubscribed"
            :class="{ 'subscribed': item.isSubscribed }"
          >
            {{ item.isSubscribed ? '已订阅' : '订阅' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { useRouter } from 'vue-router'
import FixedNavbar from '@/components/common/FixedNavbar.vue'

const strategies = ref([])
const myStrategies = ref([])
const subscribedStrategies = ref([])
const router = useRouter()

// 存储图表实例
const chartInstances = ref({})

// 跳转到策略详情页面
const goToStrategyDetail = (strategyItem) => {
  // 跳转到策略详情页面，传递策略ID或策略名称
  router.push({
    name: 'strategyDetail',
    params: { id: strategyItem.id },
    query: { strategyName: strategyItem.strategyName }
  })
}

// 订阅策略函数
const subscribeStrategy = async (strategyItem) => {
  try {
    // 发送订阅请求
    const response = await axios.post('/api/strategy/subscribeStrategy/', {
      strategyId: strategyItem.id,
      strategyName: strategyItem.strategyName
    }, {
      withCredentials: true
    })

    if (response.data.success) {
      // 更新UI状态
      strategyItem.isSubscribed = true
      alert(`成功订阅策略: ${strategyItem.strategyName}`)

      // 这里可以触发一个全局事件，通知其他组件更新
      // 或者刷新页面数据
    } else {
      alert('订阅失败: ' + response.data.message)
    }
  } catch (error) {
    console.error('订阅策略失败:', error)
    alert('订阅失败，请稍后重试')
  }

  // 阻止事件冒泡，避免同时触发卡片点击事件
  event.stopPropagation()
}

// 初始化图表
const initChart = (strategyItem) => {
  const chartContainer = document.getElementById(`chart-${strategyItem.id}`)
  if (!chartContainer || !strategyItem.chartData) return

  // 销毁已存在的图表实例
  if (chartInstances.value[strategyItem.id]) {
    chartInstances.value[strategyItem.id].dispose()
  }

  const chart = echarts.init(chartContainer)

  // 保存图表实例以便后续销毁
  chartInstances.value[strategyItem.id] = chart

  // 格式化日期
  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const year = dateStr.slice(0, 4)
    const month = dateStr.slice(4, 6)
    const day = dateStr.slice(6, 8)
    return `${year}-${month}-${day}`
  }

  const option = {
    title: {
      text: '回测数据图',
      textStyle: {
        fontSize: 14,
        fontWeight: 'normal'
      },
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        let date = params[0].name
        let formattedDate = formatDate(date)
        let content = `${formattedDate}<br/>`

        for (let i = 0; i < params.length; i++) {
          content += `${params[i].seriesName} : ${params[i].value.toFixed(2)}%<br/>`
        }

        if (strategyItem.chartData.ShareHolding_stock && strategyItem.chartData.ShareHolding_stock[date]) {
          const stocks = strategyItem.chartData.ShareHolding_stock[date]
          content += `当日持仓: ${stocks.join(', ')}`
        } else {
          content += '当日持仓: 空仓'
        }

        return content
      }
    },
    legend: {
      data: ['基准收益率', '策略收益率'],
      top: 20
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
      data: strategyItem.chartData.dates || [],
      axisLabel: {
        fontSize: 8,
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}%',
        fontSize: 8
      }
    },
    series: [
      {
        name: '基准收益率',
        type: 'line',
        data: strategyItem.chartData.benchmarkReturns?.map(v => (v * 100)) || [],
        lineStyle: { color: 'red' },
        itemStyle: { color: 'red' },
        smooth: true
      },
      {
        name: '策略收益率',
        type: 'line',
        data: strategyItem.chartData.strategyReturns?.map(v => (v * 100)) || [],
        lineStyle: { color: 'blue' },
        itemStyle: { color: 'blue' },
        smooth: true
      }
    ]
  }

  chart.setOption(option)

  // 监听窗口大小变化，重新调整图表大小
  const handleResize = () => {
    chart.resize()
  }

  window.addEventListener('resize', handleResize)

  // 将resize处理函数存储到策略项中，以便后续清理
  strategyItem.resizeHandler = handleResize
}

// 加载策略配置和回测数据
const loadStrategyData = async (strategyItem) => {
  try {
    const response = await axios.post('/api/strategy/loadStrategyConfig/', {
      strategyName: strategyItem.strategyName
    }, {
      withCredentials: true
    })

    if (response.data.success && response.data.backtest_result) {
      strategyItem.chartData = response.data.backtest_result

      // 更新其他数据
      if (response.data.backtest_result.metrics) {
        const metrics = response.data.backtest_result.metrics
        if (metrics.strategy) {
          strategyItem.annualReturn = `${(metrics.strategy.annualizedReturn * 100).toFixed(1)}%`
          strategyItem.maxDrawdown = `${(metrics.strategy.maxDrawdown * 100).toFixed(1)}%`
        }
      }
    }
  } catch (error) {
    console.error('加载策略数据失败:', error)
  }
}

// 初始化所有图表
const initAllCharts = async () => {
  await nextTick()
  strategies.value.forEach(strategy => {
    if (strategy.chartData && strategy.chartData.dates && strategy.chartData.dates.length > 0) {
      initChart(strategy)
    }
  })
}

// 加载所有策略
const loadAllStrategies = async () => {
  try {
    const response = await axios.get('/api/strategy/getUserStrategies/', {
      withCredentials: true
    })

    if (response.data.success) {
      // 初始化策略数据
      strategies.value = response.data.strategies.map(strategy => ({
        id: strategy.id || strategy.strategyName, // 如果没有id，使用策略名称作为id
        strategyName: strategy.strategyName,
        annualReturn: '0%', // 默认值
        maxDrawdown: '0%',  // 默认值
        capital: strategy.init_fund || '0',
        userCount: strategy.userCount || 0,
        chartData: null,
        isSubscribed: strategy.isSubscribed || false, // 添加订阅状态
        incomeBase: strategy.income_base || '沪深300' // 添加收益基准
      }))

      // 分离我的策略和订阅策略
      myStrategies.value = strategies.value.filter(strategy => !strategy.isSubscribed)
      subscribedStrategies.value = strategies.value.filter(strategy => strategy.isSubscribed)

      // 为每个策略加载详细数据
      for (const strategy of strategies.value) {
        await loadStrategyData(strategy)
      }

      // 初始化所有图表
      await initAllCharts()
    }
  } catch (error) {
    console.error('加载策略列表失败:', error)
    // 显示错误信息给用户
    alert('加载策略列表失败，请稍后重试')
  }
}

// 清理函数
const cleanup = () => {
  // 销毁所有图表实例
  Object.values(chartInstances.value).forEach(chart => {
    if (chart && !chart.isDisposed()) {
      chart.dispose()
    }
  })

  // 移除所有resize事件监听器
  strategies.value.forEach(strategy => {
    if (strategy.resizeHandler) {
      window.removeEventListener('resize', strategy.resizeHandler)
    }
  })
}

onMounted(async () => {
  // 加载所有策略
  await loadAllStrategies()
})

// 在组件卸载前清理资源
import { onUnmounted } from 'vue'
onUnmounted(() => {
  cleanup()
})
</script>


<style scoped>
.user-strategy-container {
    width: 100%; /* 宽度铺满整个屏幕 */
    min-height: 100vh;
    padding: 76px 24px 32px;
    margin-top: -18px;
    box-sizing: border-box; /* 包含内边距和边框在元素的总宽度和高度内 */
}


.page-title {
  font-size: 24px;
  font-weight: bold;
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
}

.card-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.strategy-card {
    width: calc(33.33% - 40px); /* 每行三个卡牌，减去两边的间距 */
    background-color: #fff; /* 背景颜色 */
    border-radius: 8px; /* 圆角 */
    padding: 18px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* 阴影效果 */
    overflow: hidden; /* 隐藏溢出内容 */
    transition: transform 0.3s; /* 过渡效果 */
}

/* 鼠标悬停时放大 */
.strategy-card:hover {
    transform: scale(1.02);
}

.chart-container {
  width: 100%;
  height: 150px;
  position: relative;
  background-color: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 10px;
}

.strategy-chart {
  width: 100%;
  height: 100%;
}

.no-chart {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #6c757d;
  font-size: 14px;
}

.strategy-title {
  font-size: 16px;
  font-weight: bold;
  margin: 0 0 8px;
  color: #333;
}

.strategy-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 6px;
  margin: 10px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.info-label {
  color: #666;
}

.info-value {
  color: #333;
  font-weight: 500;
}

.highlight {
  color: #28a745;
  font-weight: bold;
}

.strategy-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.subscribe-btn {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.subscribe-btn:hover:not(:disabled) {
  background-color: #0056b3;
}

.subscribe-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.subscribe-btn.subscribed {
  background-color: #28a745;
  cursor: default;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .strategy-card {
    width: calc(50% - 40px); /* 平板设备上每行显示2个卡片 */
  }
}

@media (max-width: 768px) {
  .strategy-card {
    width: 100%; /* 手机设备上每行显示1个卡片 */
  }

  .strategy-info-grid {
    grid-template-columns: 1fr;
  }

  .info-item {
    justify-content: space-between;
  }

  .user-strategy-container {
    padding: 72px 16px 24px;
    margin-top: -10px;
  }
}
</style>
