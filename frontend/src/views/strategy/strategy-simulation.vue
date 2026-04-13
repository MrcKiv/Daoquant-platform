<template>
  <div class="container">
    <!-- 头部区域 -->
    <header class="header">
      <h1 class="header-title">智能策略模拟分析平台</h1>
      <p class="header-subtitle">基于机器学习的量化策略验证系统</p>
    </header>

    <!-- 控制面板 -->
    <section class="control-panel">
      <form class="strategy-form" @submit.prevent="handleSubmit">
        <!-- 第一行表单 -->
        <div class="form-row">
          <div class="input-group">
            <label for="date">选择日期</label>
            <input
              type="date"
              id="date"
              v-model="formData.date"
              :max="maxDate"
              required
            >
          </div>

          <div class="input-group">
            <label for="stockCode">股票代码</label>
            <input
              type="text"
              id="stockCode"
              v-model="formData.stockCode"
              placeholder="例：000001"
              pattern="\d{6}"
              required
            >
          </div>

          <div class="input-group">
            <label for="todayClosePrice">当日收盘价</label>
            <input
              type="number"
              id="todayClosePrice"
              step="0.01"
              :value="formatPrice(todayClosePrice)"
              readonly
            >
          </div>

          <div class="input-group button-group">
              <button
                type="button"
                class="query-btn"
                :disabled="!formValid"
                @click="handleQuery"
              >
                <span v-if="!loading">获取实时数据</span>
                <spinner v-else />
              </button>
            </div>
          </div>

        <!-- 第二行表单 -->
        <div class="form-row">
          <div class="input-group">
            <label for="predictedClosePrice">预测收盘价</label>
            <input
              type="number"
              id="predictedClosePrice"
              v-model.number="formData.predictedClosePrice"
              step="0.01"
              min="0"
              required
            >
          </div>

          <div class="input-group">
            <label for="days">模拟周期</label>
            <input
              type="number"
              id="days"
              v-model.number="formData.days"
              min="1"
              max="365"
              required
            >
          </div>

          <div class="input-group button-group">
            <button
              type="submit"
              class="submit-btn"
              :disabled="!simulationReady"
            >
              开始智能模拟
            </button>
          </div>
        </div>
      </form>
    </section>

    <!-- 指标仪表盘 -->
    <indicator-dashboard
      :macd="indicators.macd"
      :kdj="indicators.kdj"
      :wr="indicators.wr"
      :boll="indicators.boll"
      :cci="indicators.cci"
    />

    <!-- 图表区域 -->
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import IndicatorDashboard from './IndicatorDashboard.vue'
import Spinner from './LoadingSpinner.vue'


// 最大可选日期（昨天）
const maxDate = computed(() => {
  const date = new Date()
  date.setDate(date.getDate() - 1)
  return date.toISOString().split('T')[0]
})

// 响应式状态
const chartContainer = ref(null)
let chartInstance = null
const loading = ref(false)
const todayClosePrice = ref(0)

// 表单数据
const formData = reactive({
  date: maxDate.value,
  stockCode: '',
  days: 60,
  predictedClosePrice: 0
})

// 技术指标
const indicators = reactive({
  macd: null,
  kdj: null,
  wr: null,
  boll: null,
  cci: null
})

// 表单验证
const formValid = computed(() => {
  return formData.date && /^\d{6}$/.test(formData.stockCode)
})

const simulationReady = computed(() => {
  return formValid.value && formData.predictedClosePrice > 0
})

// 图表初始化
const initChart = () => {
  if (!chartContainer.value) return
  chartInstance = echarts.init(chartContainer.value)
  window.addEventListener('resize', handleResize)
}

// 窗口缩放处理
const handleResize = () => {
  chartInstance?.resize()
}

// 价格格式化
const formatPrice = (value) => {
  return value?.toFixed(2) || '--'
}

// 获取实时数据
const handleQuery = async () => {
  try {
    loading.value = true
    const { data } = await axios.get('/api/strategy/queryClosePrice/', {
      params: {
        date: formData.date,
        stockCode: formData.stockCode
      }
    })

    todayClosePrice.value = data.close_price
    formData.predictedClosePrice = data.close_price
  } catch (error) {
    showError('数据获取失败', error)
  } finally {
    loading.value = false
  }
}

// 构建图表配置
const buildChartOption = (chartData) => ({
  backgroundColor: '#1a1a1a',
  dataset: { source: chartData.klines },
  title: {
    text: `${formData.stockCode} 价格走势分析`,
    left: 'center',
    textStyle: {
      color: '#fff',
      fontSize: 18
    }
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
    backgroundColor: 'rgba(40,40,40,0.9)',
    borderWidth: 0,
    textStyle: { color: '#fff' }
  },
  grid: [
    { top: 60, left: 50, right: 50, height: '50%' },
    { top: '70%', left: 50, right: 50, height: 100 }
  ],
  xAxis: [
    { type: 'category', gridIndex: 0, boundaryGap: false },
    { type: 'category', gridIndex: 1, show: false }
  ],
  yAxis: [
    {
      gridIndex: 0,
      scale: true,
      splitArea: { show: true },
      axisLabel: { color: '#fff' }
    },
    {
      gridIndex: 1,
      splitNumber: 3,
      axisLabel: { color: '#fff' }
    }
  ],
  dataZoom: [
    {
      type: 'inside',
      xAxisIndex: [0, 1],
      start: 30,
      end: 100,
      zoomOnMouseWheel: 'shift'
    },
    {
      type: 'slider',
      xAxisIndex: [0, 1],
      bottom: 10,
      height: 20,
      handleStyle: { color: '#666' }
    }
  ],
  series: [
    // K线图
    {
      type: 'candlestick',
      itemStyle: {
        color: '#ef232a',
        color0: '#14b143',
        borderColor: null,
        borderColor0: null
      },
      emphasis: {
        itemStyle: {
          borderWidth: 1,
          shadowBlur: 10,
          shadowColor: 'rgba(255,255,255,0.3)'
        }
      },
      encode: { x: 0, y: [1, 2, 3, 4] }
    },
    // 成交量
    {
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      itemStyle: {
        color: params => params.value[5] > 0 ? '#ef232a' : '#14b143'
      },
      encode: { x: 0, y: 5 }
    }
  ]
})

// 提交策略模拟
const handleSubmit = async () => {
  try {
    loading.value = true
    console.log('FormData:', formData); // 添加这行代码
    const { data } = await axios.get('/api/strategy/getKlineChart/', {
      params: {
        date: formData.date,
        days: formData.days,
        stockCode: formData.stockCode,
        predictedClosePrice: formData.predictedClosePrice
      }
    })

    // 更新指标数据
    Object.assign(indicators, data.indicators)

    // 更新图表
    if (chartInstance) {
      chartInstance.setOption(buildChartOption(data.chart_data))
    }
  } catch (error) {
    showError('策略模拟失败', error)
  } finally {
    loading.value = false
  }
}

// 错误处理
const showError = (title, error) => {
  console.error(`${title}:`, error)
  alert(`${title}: ${error.response?.data?.message || error.message}`)
}

// 生命周期
onMounted(initChart)
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style lang="scss" scoped>
/* 全屏容器 */
.container {
  width: 100%;
  min-height: 100vh;
  margin: 0;
  padding: 0;
  background: #f8f9fa;
  box-sizing: border-box;
}

/* 全宽头部 */
.header {
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px;
  background: linear-gradient(135deg, #2c3e50, #3498db);
  color: white;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  text-align: center;

  &-title {
    font-size: 2.2rem;
    margin-bottom: 12px;
  }

  &-subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    max-width: 80%;
    margin: 0 auto;
  }
}

/* 控制面板 */
.control-panel {
  width: 100%;
  max-width: 1440px;
  margin: 0 auto 32px;
  padding: 24px;
  background: white;
  box-shadow: 0 2px 15px rgba(0,0,0,0.08);
}

/* 表单布局 - 关键修改 */
.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
  align-items: end; /* 底部对齐 */

  &:last-child {
    margin-bottom: 0;
  }
}

/* 输入组件 */
.input-group {
  display: flex;
  flex-direction: column;
  height: 100%; /* 等高布局 */

  label {
    font-weight: 600;
    margin-bottom: 8px;
    color: #2c3e50;
    font-size: 0.95rem;
    height: 28px; /* 固定标签高度 */
  }

  /* 按钮容器特殊处理 */
  &.button-group {
    margin-top: 28px; /* 补偿标签高度 */
    height: calc(100% - 28px); /* 自动计算剩余高度 */

    button {
      margin-top: auto; /* 底部对齐 */
    }
  }

  input {
    padding: 12px 16px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    font-size: 1rem;
    transition: all 0.2s ease;
    width: 100%;

    &:focus {
      border-color: #3498db;
      box-shadow: 0 0 0 3px rgba(52,152,219,0.15);
    }

    &[readonly] {
      background: #f8f9fa;
      cursor: not-allowed;
    }
  }
}

/* 按钮样式 */
button {
  padding: 14px 24px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
}

.query-btn {
  background: #3498db;
  color: white;

  &:hover:not(:disabled) {
    background: #2980b9;
    transform: translateY(-1px);
  }
}

.submit-btn {
  background: #27ae60;
  color: white;

  &:hover:not(:disabled) {
    background: #219a52;
    box-shadow: 0 3px 12px rgba(39,174,96,0.3);
  }
}

/* 图表容器 */
.chart-container {
  width: 100%;
  height: 680px;
  max-width: 1440px;
  margin: 32px auto 0;
  background: white;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .header {
    padding: 24px 16px !important;

    &-title {
      font-size: 1.8rem;
    }

    &-subtitle {
      font-size: 1rem;
    }
  }

  .control-panel {
    padding: 16px;
  }

  .input-group {
    &.button-group {
      margin-top: 0;
      height: auto;

      button {
        height: 48px;
        margin-top: 8px;
      }
    }
  }

  .chart-container {
    height: 500px;
    margin-top: 24px;
  }
}
</style>