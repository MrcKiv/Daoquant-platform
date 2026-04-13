<template>
  <section class="strategy-selection">
    <h2 class="section-title">我的策略</h2>
    <div class="card-container">
      <div
        v-for="(item, index) in strategies"
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
  </section>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { useRouter } from 'vue-router'

const strategies = ref([])
const router = useRouter()

// 存储图表实例
const chartInstances = ref({})
const userStore = useUserStore()

// 跳转到策略详情页面（带访问控制）
const goToStrategyDetail = async (strategyItem) => {
  // 检查用户登录状态
  if (!userStore.isLoggedIn) {
    try {
      await ElMessageBox.confirm(
        '您尚未登录，是否前往登录页面？',
        '请先登录',
        {
          confirmButtonText: '去登录',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
      router.push('/login')
    } catch {
      // 用户点击了取消，不执行任何操作
    }
    return
  }

  // 跳转到策略详情页面，传递策略ID或策略名称
  router.push({
    name: 'strategyDetail',
    params: { id: strategyItem.id },
    query: { strategyName: strategyItem.strategyName }
  })
}

// 订阅策略函数
const subscribeStrategy = async (strategyItem) => {
   // 检查用户登录状态
  if (!userStore.isLoggedIn) {
    try {
      await ElMessageBox.confirm(
        '您尚未登录，是否前往登录页面？',
        '请先登录',
        {
          confirmButtonText: '去登录',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
      router.push('/login')
    } catch {
      // 用户点击了取消，不执行任何操作
    }
    return
  }
  try {
    // 发送订阅请求
    const response = await axios.post('/api/strategy/subscribeStrategy/', {
      strategyId: strategyItem.id,
      strategyName: strategyItem.strategyName,
       userId: strategyItem.userID // 添加userID参数
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
import {useUserStore} from "@/stores/user.js";
onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
@import '@/assets/css/common/Third.css';

.chart-container {
  width: 100%;
  height: 150px; /* 与原图片高度一致 */
  position: relative;
  background-color: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 15px;
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
  margin: 10px 0;
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
@media (max-width: 768px) {
  .strategy-info-grid {
    grid-template-columns: 1fr;
  }

  .info-item {
    justify-content: space-between;
  }
}
</style>
