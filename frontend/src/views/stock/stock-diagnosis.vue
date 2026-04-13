<template>
  <FixedNavbar />
  <div class="stock-diagnosis">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>个股诊断</h1>
      <p>专业的股票技术分析与投资建议</p>
    </div>

    <!-- 主要指数展示 -->
    <div class="index-section">
      <h2>主要指数</h2>
      <div class="index-grid">
        <div 
          v-for="index in indexData.slice(0, 8)" 
          :key="index.ts_code" 
          class="index-card"
          :class="{ active: selectedIndex === index.ts_code }"
          @click="selectIndex(index)"
        >
          <div class="index-name">{{ getIndexName(index.ts_code) }}</div>
          <div class="index-price">{{ formatPrice(index.close) }}</div>
          <div class="index-change" :class="getChangeClass(index.pct_chg)">
            {{ formatChange(index.pct_chg) }}
          </div>
        </div>
      </div>
      <div class="index-more" v-if="indexData.length > 8">
        显示前8个主要指数，共{{ indexData.length }}个指数
      </div>
    </div>

    <!-- 默认指数图表 -->
    <div v-if="!selectedStock" class="default-chart-section">
      <h2>{{ getIndexName(selectedIndex) }} 走势图</h2>
      <div class="chart-description">
        <p><strong>图表说明：</strong></p>
        <ul>
          <li><strong>主图：</strong>K线图 + 移动平均线(MA5/MA10/MA20)</li>
          <li><strong>副图1：</strong>成交量</li>
          <li><strong>副图2：</strong>MACD指标(DIF线、DEA线、柱状图)</li>
          <li><strong>副图3：</strong>RSI指标(超买线70、超卖线30)</li>
        </ul>
      </div>
      <div id="defaultIndexChart" class="chart-container"></div>
    </div>

    <!-- 股票搜索 -->
    <div class="search-section">
      <h2>股票搜索</h2>
      <div class="search-box">
        <input 
          v-model="searchQuery" 
          @input="handleSearch"
          placeholder="输入股票代码、名称或行业关键词..."
          class="search-input"
        />
        <button @click="performSearch" class="search-btn">搜索</button>
      </div>
      
      <!-- 搜索结果 -->
      <div v-if="searchResults.length > 0" class="search-results">
        <div 
          v-for="stock in searchResults" 
          :key="stock.st_code"
          @click="selectStock(stock)"
          class="stock-item"
        >
          <div class="stock-header">
            <div class="stock-code">{{ stock.st_code }}</div>
            <div class="stock-name">{{ stock.name }}</div>
          </div>
                     <div class="stock-details">
             <div class="stock-info">
               <span class="industry">{{ stock.industry }}</span>
               <span class="area">{{ stock.area }}</span>
             </div>
             <div class="stock-market">
               <span class="market">{{ stock.market }}</span>
             </div>
           </div>
        </div>
      </div>
    </div>

    <!-- 股票详情 -->
    <div v-if="selectedStock" class="stock-detail">
      <h2>{{ selectedStock.name }} ({{ selectedStock.st_code }})</h2>
      
      <!-- 基本信息 -->
      <div class="basic-info">
        <div class="info-item">
          <span class="label">行业：</span>
          <span class="value">{{ selectedStock.industry }}</span>
        </div>
        <div class="info-item">
          <span class="label">地区：</span>
          <span class="value">{{ selectedStock.area }}</span>
        </div>
        <div class="info-item">
          <span class="label">市场：</span>
          <span class="value">{{ selectedStock.market }}</span>
        </div>
      </div>

      <!-- 技术分析图表 -->
      <div class="chart-section">
        <h3>技术分析图表</h3>
        <div class="chart-controls">
          <button 
            v-for="period in chartPeriods" 
            :key="period.value"
            @click="changeChartPeriod(period.value)"
            :class="['period-btn', { active: currentPeriod === period.value }]"
          >
            {{ period.label }}
          </button>
        </div>
        <div class="chart-description">
          <p><strong>图表说明：</strong></p>
          <ul>
            <li><strong>主图：</strong>K线图 + 移动平均线(MA5/MA10/MA20) + 布林带</li>
            <li><strong>副图1：</strong>成交量</li>
            <li><strong>副图2：</strong>MACD指标(DIF线、DEA线、柱状图)</li>
            <li><strong>副图3：</strong>RSI指标(超买线70、超卖线30)</li>
<!--            <li><strong>副图4：</strong>KDJ指标(K线、D线、J线)</li>-->
          </ul>
        </div>
        <div id="klineChart" class="chart-container"></div>
      </div>

      <!-- 技术指标 -->
<!--      <div class="indicators-section">-->
<!--        <h3>技术指标</h3>-->
<!--        <div class="indicators-grid">-->
<!--          <div class="indicator-card">-->
<!--            <div class="indicator-name">MACD</div>-->
<!--            <div class="indicator-value">{{ formatIndicatorValue(latestData.macd_macd) }}</div>-->
<!--            <div class="indicator-status" :class="getMacdStatus()">-->
<!--              {{ getMacdStatusText() }}-->
<!--            </div>-->
<!--          </div>-->
<!--          <div class="indicator-card">-->
<!--            <div class="indicator-name">RSI</div>-->
<!--            <div class="indicator-value">{{ formatIndicatorValue(latestData.rsi) }}</div>-->
<!--            <div class="indicator-status" :class="getRsiStatus()">-->
<!--              {{ getRsiStatusText() }}-->
<!--            </div>-->
<!--          </div>-->
<!--          <div class="indicator-card">-->
<!--            <div class="indicator-name">KDJ</div>-->
<!--            <div class="indicator-value">K:{{ formatIndicatorValue(latestData.kdj_k) }} D:{{ formatIndicatorValue(latestData.kdj_d) }}</div>-->
<!--            <div class="indicator-status" :class="getKdjStatus()">-->
<!--              {{ getKdjStatusText() }}-->
<!--            </div>-->
<!--          </div>-->
<!--          <div class="indicator-card">-->
<!--            <div class="indicator-name">BOLL</div>-->
<!--            <div class="indicator-value">{{ formatIndicatorValue(latestData.boll_boll) }}</div>-->
<!--            <div class="indicator-status" :class="getBollStatus()">-->
<!--              {{ getBollStatusText() }}-->
<!--            </div>-->
<!--          </div>-->
<!--        </div>-->
<!--      </div>-->

      <!-- 诊断结果 -->
      <div v-if="diagnosisResult" class="diagnosis-section">
        <h3>诊断结果</h3>
        <div class="diagnosis-summary">
          <div class="score-card overall">
            <div class="score-title">综合评分</div>
            <div class="score-value">{{ diagnosisResult.overall_score }}</div>
            <div class="score-label">{{ diagnosisResult.recommendation }}</div>
          </div>
          <div class="score-card technical">
            <div class="score-title">技术面</div>
            <div class="score-value">{{ diagnosisResult.technical_score }}</div>
            <div class="score-label">技术分析</div>
          </div>
          <div class="score-card fundamental">
            <div class="score-title">基本面</div>
            <div class="score-value">{{ diagnosisResult.fundamental_score }}</div>
            <div class="score-label">基本面分析</div>
          </div>
        </div>
        
        <div class="diagnosis-details">
          <div class="detail-section">
            <h4>技术面分析</h4>
            <ul>
              <li v-for="(analysis, index) in diagnosisResult.technical_analysis" :key="index">
                {{ analysis }}
              </li>
            </ul>
          </div>
          
          <div class="detail-section">
            <h4>投资建议</h4>
            <div class="recommendation" :class="getRecommendationClass()">
              {{ diagnosisResult.recommendation }}
            </div>
            <div class="risk-level">
              风险等级：<span :class="getRiskClass()">{{ diagnosisResult.risk_level }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import FixedNavbar from '@/components/common/FixedNavbar.vue'
import * as echarts from 'echarts'

// 响应式数据
const searchQuery = ref('')
const searchResults = ref([])
const selectedStock = ref(null)
const selectedIndex = ref('000001.SH') // 默认选中上证综指
const indexData = ref([])
const chartData = ref(null)
const latestData = ref({})
const diagnosisResult = ref(null)
const currentPeriod = ref('daily')
const klineChart = ref(null)

// 图表周期选项
const chartPeriods = [
  { label: '日K', value: 'daily' },
  { label: '周K', value: 'weekly' },
  { label: '月K', value: 'monthly' }
]

// 获取指数名称
const getIndexName = (tsCode) => {
  const names = {
    '000001.SH': '上证综指',
    '399001.SZ': '深证成指',
    '399006.SZ': '创业板指'
  }
  return names[tsCode] || tsCode
}

// 格式化价格
const formatPrice = (price) => {
  if (!price) return '--'
  return parseFloat(price).toFixed(2)
}

// 格式化涨跌幅
const formatChange = (change) => {
  if (!change) return '--'
  const value = parseFloat(change)
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

// 获取涨跌样式类
const getChangeClass = (change) => {
  if (!change) return ''
  const value = parseFloat(change)
  return value > 0 ? 'positive' : value < 0 ? 'negative' : ''
}

// 获取价格变化样式类
const getPriceChangeClass = (change) => {
  if (!change) return ''
  const value = parseFloat(change)
  return value > 0 ? 'positive' : value < 0 ? 'negative' : ''
}

// 处理搜索输入
const handleSearch = () => {
  if (searchQuery.value.length >= 2) {
    performSearch()
  } else {
    searchResults.value = []
  }
}

// 执行搜索
const performSearch = async () => {
  if (!searchQuery.value.trim()) return
  
  try {
    const response = await fetch(`/api/stock_analysis/search/?q=${encodeURIComponent(searchQuery.value)}`)
    const data = await response.json()
    if (data.results) {
      searchResults.value = data.results
    }
  } catch (error) {
    console.error('搜索失败:', error)
  }
}

// 选择股票
const selectStock = async (stock) => {
  selectedStock.value = stock
  searchResults.value = []
  searchQuery.value = stock.name
  
  // 获取股票详细信息
  await loadStockData(stock.st_code)
}

// 选择指数
const selectIndex = async (index) => {
  selectedIndex.value = index.ts_code
  selectedStock.value = null // 清除选中的股票
  searchResults.value = []
  searchQuery.value = ''
  
  // 获取指数详细信息
  await loadIndexData(index.ts_code)
}

// 加载股票数据
const loadStockData = async (stockCode) => {
  try {
    // 获取股票信息
    const infoResponse = await fetch(`/api/stock_analysis/stock/${stockCode}/`)
    const infoData = await infoResponse.json()
    
    if (infoData.basic_info) {
      selectedStock.value = { ...selectedStock.value, ...infoData.basic_info }
    }
    
    // 获取图表数据
    const chartResponse = await fetch(`/api/stock_analysis/chart/${stockCode}/`)
    const chartDataResponse = await chartResponse.json()
    console.log('图表数据:', chartDataResponse)
    
    if (chartDataResponse.dates) {
      // 处理日期格式，将Timestamp转换为字符串
      const processedChartData = {
        ...chartDataResponse,
        dates: chartDataResponse.dates.map(date => {
          if (typeof date === 'object' && date !== null) {
            // 如果是Timestamp对象，转换为YYYY-MM-DD格式
            if (date.toISOString) {
              return date.toISOString().split('T')[0]
            } else if (date.toString) {
              return date.toString()
            }
          }
          return date
        })
      }
      
      chartData.value = processedChartData
      await nextTick()
      initKlineChart()
    }
    
    // 获取诊断结果
    if (infoData.diagnosis) {
      diagnosisResult.value = infoData.diagnosis
    }
    
    // 获取最新数据
    if (infoData.latest_quote) {
      latestData.value = infoData.latest_quote
    } else if (infoData.daily_data && infoData.daily_data.length > 0) {
      latestData.value = infoData.daily_data[infoData.daily_data.length - 1]
    }
    
  } catch (error) {
    console.error('加载股票数据失败:', error)
  }
}

// 加载指数数据
const loadIndexData = async (tsCode) => {
  try {
    const response = await fetch(`/api/stock_analysis/index/${tsCode}/`)
    const data = await response.json()
    
    if (data.dates) {
      // 处理日期格式，将Timestamp转换为字符串
      const processedChartData = {
        ...data,
        dates: data.dates.map(date => {
          if (typeof date === 'object' && date !== null) {
            // 如果是Timestamp对象，转换为YYYY-MM-DD格式
            if (date.toISOString) {
              return date.toISOString().split('T')[0]
            } else if (date.toString) {
              return date.toString()
            }
          }
          return date
        })
      }
      
      chartData.value = processedChartData
      await nextTick()
      initDefaultIndexChart()
    }
  } catch (error) {
    console.error('加载指数数据失败:', error)
  }
}

// 改变图表周期
const changeChartPeriod = async (period) => {
  currentPeriod.value = period
  if (selectedStock.value) {
    await loadStockData(selectedStock.value.st_code)
  }
}

// 初始化K线图
const initKlineChart = () => {
  if (!chartData.value) return
  
  const chartDom = document.getElementById('klineChart')
  if (!chartDom) return
  
  if (klineChart.value) {
    klineChart.value.dispose()
  }
  
  klineChart.value = echarts.init(chartDom)
  
  const option = {
    title: {
      text: `${selectedStock.value.name} 技术分析图`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', '成交量', 'MACD', 'RSI',  'BOLL-上轨', 'BOLL-中轨', 'BOLL-下轨'],
      top: 30
    },
    grid: [
      {
        left: '10%',
        right: '10%',
        height: '35%'
      },
      {
        left: '10%',
        right: '10%',
        top: '42%',
        height: '12%'
      },
      {
        left: '10%',
        right: '10%',
        top: '57%',
        height: '12%'
      },
      {
        left: '10%',
        right: '10%',
        top: '72%',
        height: '12%'
      },
      {
        left: '10%',
        right: '10%',
        top: '87%',
        height: '12%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 1,
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 2,
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 3,
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 4,
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ],
    yAxis: [
      {
        scale: true,
        splitArea: {
          show: true
        }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      },
      {
        scale: true,
        gridIndex: 2,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      },
      {
        scale: true,
        gridIndex: 3,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      },
      {
        scale: true,
        gridIndex: 4,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1, 2, 3, 4],
        start: 50,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1, 2, 3, 4],
        type: 'slider',
        top: '95%',
        start: 50,
        end: 100
      }
    ],
    series: [
      // K线图
      {
        name: 'K线',
        type: 'candlestick',
        data: chartData.value.dates.map((date, index) => [
          chartData.value.prices.open[index],
          chartData.value.prices.close[index],
          chartData.value.prices.low[index],
          chartData.value.prices.high[index]
        ]),
        itemStyle: {
          color: '#ec0000',
          color0: '#00da3c',
          borderColor: '#ec0000',
          borderColor0: '#00da3c'
        }
      },
      // 移动平均线
      {
        name: 'MA5',
        type: 'line',
        data: chartData.value.indicators.ma5,
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#ff7f50'
        }
      },
      {
        name: 'MA10',
        type: 'line',
        data: chartData.value.indicators.ma10,
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#87ceeb'
        }
      },
      {
        name: 'MA20',
        type: 'line',
        data: chartData.value.indicators.ma20,
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#da70d6'
        }
      },
      // 成交量
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: chartData.value.volume,
        itemStyle: {
          color: '#91cc75'
        }
      },
      // MACD
      {
        name: 'MACD',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: chartData.value.indicators.macd,
        lineStyle: {
          color: '#5470c6'
        }
      },
      {
        name: 'MACD信号线',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: chartData.value.indicators.macd_signal,
        lineStyle: {
          color: '#91cc75'
        }
      },
      {
        name: 'MACD柱状图',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: chartData.value.indicators.macd_histogram,
        itemStyle: {
          color: function(params) {
            return params.data >= 0 ? '#ec0000' : '#00da3c'
          }
        }
      },
      // RSI
      {
        name: 'RSI',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: chartData.value.indicators.rsi,
        lineStyle: {
          color: '#fac858'
        }
      },
      {
        name: 'RSI超买线',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: Array(chartData.value.dates.length).fill(70),
        lineStyle: {
          color: '#ee6666',
          type: 'dashed'
        }
      },
      {
        name: 'RSI超卖线',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: Array(chartData.value.dates.length).fill(30),
        lineStyle: {
          color: '#73c0de',
          type: 'dashed'
        }
      },
      // KDJ
      {
        name: 'KDJ-K',
        type: 'line',
        xAxisIndex: 4,
        yAxisIndex: 4,
        data: chartData.value.indicators.kdj_k,
        lineStyle: {
          color: '#5470c6'
        }
      },
      {
        name: 'KDJ-D',
        type: 'line',
        xAxisIndex: 4,
        yAxisIndex: 4,
        data: chartData.value.indicators.kdj_d,
        lineStyle: {
          color: '#91cc75'
        }
      },
      {
        name: 'KDJ-J',
        type: 'line',
        xAxisIndex: 4,
        yAxisIndex: 4,
        data: chartData.value.indicators.kdj_j,
        lineStyle: {
          color: '#fac858'
        }
      },
      // 布林带
      {
        name: 'BOLL-上轨',
        type: 'line',
        data: chartData.value.indicators.boll_upper,
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#ee6666',
          type: 'dashed'
        }
      },
      {
        name: 'BOLL-中轨',
        type: 'line',
        data: chartData.value.indicators.boll_middle,
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#5470c6'
        }
      },
      {
        name: 'BOLL-下轨',
        type: 'line',
        data: chartData.value.indicators.boll_lower,
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#73c0de',
          type: 'dashed'
        }
      }
    ]
  }
  
  klineChart.value.setOption(option)
}

// 初始化默认指数图表
const initDefaultIndexChart = () => {
  if (!chartData.value) return
  
  const chartDom = document.getElementById('defaultIndexChart')
  if (!chartDom) return
  
  if (klineChart.value) {
    klineChart.value.dispose()
  }
  
  klineChart.value = echarts.init(chartDom)
  
  const option = {
    title: {
      text: `${getIndexName(selectedIndex.value)}`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', '成交量', 'MACD', 'RSI'],
      top: 30
    },
    grid: [
      {
        left: '10%',
        right: '10%',
        height: '35%'
      },
      {
        left: '10%',
        right: '10%',
        top: '42%',
        height: '12%'
      },
      {
        left: '10%',
        right: '10%',
        top: '57%',
        height: '12%'
      },
      {
        left: '10%',
        right: '10%',
        top: '72%',
        height: '12%'
      }
    ],
    xAxis: [
      {
        type: 'category',
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 1,
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 2,
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      },
      {
        type: 'category',
        gridIndex: 3,
        data: chartData.value.dates,
        scale: true,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ],
    yAxis: [
      {
        scale: true,
        splitArea: {
          show: true
        }
      },
      {
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      },
      {
        scale: true,
        gridIndex: 2,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      },
      {
        scale: true,
        gridIndex: 3,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1, 2, 3],
        start: 50,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1, 2, 3],
        type: 'slider',
        top: '95%',
        start: 50,
        end: 100
      }
    ],
    series: [
      // K线图
      {
        name: 'K线',
        type: 'candlestick',
        data: chartData.value.dates.map((date, index) => [
          chartData.value.prices.open[index],
          chartData.value.prices.close[index],
          chartData.value.prices.low[index],
          chartData.value.prices.high[index]
        ]),
        itemStyle: {
          color: '#ec0000',
          color0: '#00da3c',
          borderColor: '#ec0000',
          borderColor0: '#00da3c'
        }
      },
      // 移动平均线
      {
        name: 'MA5',
        type: 'line',
        data: chartData.value.indicators.ma5 || [],
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#ff7f50'
        }
      },
      {
        name: 'MA10',
        type: 'line',
        data: chartData.value.indicators.ma10 || [],
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#87ceeb'
        }
      },
      {
        name: 'MA20',
        type: 'line',
        data: chartData.value.indicators.ma20 || [],
        smooth: true,
        lineStyle: {
          opacity: 0.5,
          color: '#da70d6'
        }
      },
      // 成交量
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: chartData.value.volume,
        itemStyle: {
          color: '#91cc75'
        }
      },
      // MACD
      {
        name: 'MACD',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: chartData.value.indicators.macd || [],
        lineStyle: {
          color: '#5470c6'
        }
      },
      {
        name: 'MACD信号线',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: chartData.value.indicators.macd_signal || [],
        lineStyle: {
          color: '#91cc75'
        }
      },
      {
        name: 'MACD柱状图',
        type: 'bar',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: chartData.value.indicators.macd_histogram || [],
        itemStyle: {
          color: function(params) {
            return params.data >= 0 ? '#ec0000' : '#00da3c'
          }
        }
      },
      // RSI
      {
        name: 'RSI',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: chartData.value.indicators.rsi || [],
        lineStyle: {
          color: '#fac858'
        }
      },
      {
        name: 'RSI超买线',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: Array(chartData.value.dates.length).fill(70),
        lineStyle: {
          color: '#ee6666',
          type: 'dashed'
        }
      },
      {
        name: 'RSI超卖线',
        type: 'line',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: Array(chartData.value.dates.length).fill(30),
        lineStyle: {
          color: '#73c0de',
          type: 'dashed'
        }
      }
    ]
  }
  
  klineChart.value.setOption(option)
}

// 格式化指标值
const formatIndicatorValue = (value) => {
  if (value === null || value === undefined) return '--'
  return parseFloat(value).toFixed(2)
}

// MACD状态
const getMacdStatus = () => {
  if (!latestData.value.macd_macd) return ''
  return parseFloat(latestData.value.macd_macd) > 0 ? 'positive' : 'negative'
}

const getMacdStatusText = () => {
  if (!latestData.value.macd_macd) return '--'
  return parseFloat(latestData.value.macd_macd) > 0 ? '金叉' : '死叉'
}

// RSI状态
const getRsiStatus = () => {
  if (!latestData.value.rsi) return ''
  const rsi = parseFloat(latestData.value.rsi)
  if (rsi > 70) return 'overbought'
  if (rsi < 30) return 'oversold'
  return 'normal'
}

const getRsiStatusText = () => {
  if (!latestData.value.rsi) return '--'
  const rsi = parseFloat(latestData.value.rsi)
  if (rsi > 70) return '超买'
  if (rsi < 30) return '超卖'
  return '正常'
}

// KDJ状态
const getKdjStatus = () => {
  if (!latestData.value.kdj_k || !latestData.value.kdj_d) return ''
  const k = parseFloat(latestData.value.kdj_k)
  const d = parseFloat(latestData.value.kdj_d)
  return k > d ? 'positive' : 'negative'
}

const getKdjStatusText = () => {
  if (!latestData.value.kdj_k || !latestData.value.kdj_d) return '--'
  const k = parseFloat(latestData.value.kdj_k)
  const d = parseFloat(latestData.value.kdj_d)
  return k > d ? '金叉' : '死叉'
}

// BOLL状态
const getBollStatus = () => {
  if (!latestData.value.close || !latestData.value.boll_boll) return ''
  const close = parseFloat(latestData.value.close)
  const boll = parseFloat(latestData.value.boll_boll)
  return close > boll ? 'positive' : 'negative'
}

const getBollStatusText = () => {
  if (!latestData.value.close || !latestData.value.boll_boll) return '--'
  const close = parseFloat(latestData.value.close)
  const boll = parseFloat(latestData.value.boll_boll)
  return close > boll ? '上轨' : '下轨'
}

// 建议样式
const getRecommendationClass = () => {
  if (!diagnosisResult.value) return ''
  const rec = diagnosisResult.value.recommendation
  if (rec === '买入') return 'buy'
  if (rec === '卖出') return 'sell'
  return 'hold'
}

// 风险等级样式
const getRiskClass = () => {
  if (!diagnosisResult.value) return ''
  const risk = diagnosisResult.value.risk_level
  if (risk === '低风险') return 'low-risk'
  if (risk === '高风险') return 'high-risk'
  return 'medium-risk'
}

// 页面加载时获取指数数据
onMounted(async () => {
  try {
    const response = await fetch('/api/stock_analysis/index/')
    const data = await response.json()
    if (data.index_data) {
      // 去重处理：只保留每个ts_code的最新数据
      const uniqueIndexData = []
      const seenCodes = new Set()
      
      // 按ts_code分组，保留最新的数据
      data.index_data.forEach(index => {
        if (!seenCodes.has(index.ts_code)) {
          seenCodes.add(index.ts_code)
          uniqueIndexData.push(index)
        }
      })
      
      // 按重要性排序：上证综指、沪深300、深证成指等优先
      const priorityOrder = [
        '000001.SH', // 上证综指
        '000300.SH', // 沪深300
        '399001.SZ', // 深证成指
        '399006.SZ', // 创业板指
        '000688.SH', // 科创板50
        '000016.SH', // 上证50
        '000905.SH', // 中证500
        '000852.SH'  // 中证1000
      ]
      
      uniqueIndexData.sort((a, b) => {
        const aPriority = priorityOrder.indexOf(a.ts_code)
        const bPriority = priorityOrder.indexOf(b.ts_code)
        
        // 如果都在优先级列表中，按优先级排序
        if (aPriority !== -1 && bPriority !== -1) {
          return aPriority - bPriority
        }
        // 如果只有一个在优先级列表中，优先级高的排在前面
        if (aPriority !== -1) return -1
        if (bPriority !== -1) return 1
        // 都不在优先级列表中，按ts_code排序
        return a.ts_code.localeCompare(b.ts_code)
      })
      
      indexData.value = uniqueIndexData
      
      // 默认选中上证综指，如果没有则选择第一个
      if (indexData.value.length > 0) {
        const shanghaiIndex = indexData.value.find(index => index.ts_code === '000001.SH')
        selectedIndex.value = shanghaiIndex ? shanghaiIndex.ts_code : indexData.value[0].ts_code
        await loadIndexData(selectedIndex.value)
      }
    }
  } catch (error) {
    console.error('获取指数数据失败:', error)
  }
})
</script>

<style scoped>
.stock-diagnosis {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-header p {
  font-size: 1.1rem;
  color: #7f8c8d;
}

/* 指数部分 */
.index-section {
  margin-bottom: 40px;
}

.index-section h2 {
  font-size: 1.8rem;
  color: #2c3e50;
  margin-bottom: 20px;
}

.index-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.index-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.index-name {
  font-size: 1.1rem;
  margin-bottom: 10px;
  opacity: 0.9;
}

.index-price {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 8px;
}

.index-change {
  font-size: 1rem;
  padding: 4px 12px;
  border-radius: 20px;
  display: inline-block;
}

.index-change.positive {
  background-color: rgba(46, 204, 113, 0.2);
  color: #2ecc71;
}

.index-change.negative {
  background-color: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.index-card.active {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  transform: scale(1.05);
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
}

.index-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  cursor: pointer;
}

.index-more {
  text-align: center;
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-top: 15px;
  font-style: italic;
}

/* 搜索部分 */
.search-section {
  margin-bottom: 40px;
}

.search-section h2 {
  font-size: 1.8rem;
  color: #2c3e50;
  margin-bottom: 20px;
}

.search-box {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #3498db;
}

.search-btn {
  padding: 12px 24px;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s;
}

.search-btn:hover {
  background-color: #2980b9;
}

.search-results {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.stock-item {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: all 0.2s;
}

.stock-item:hover {
  background-color: #f8f9fa;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.stock-item:last-child {
  border-bottom: none;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.stock-code {
  font-weight: bold;
  color: #2c3e50;
  font-size: 1.1rem;
}

.stock-name {
  color: #34495e;
  font-weight: 500;
}

.stock-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-info {
  display: flex;
  gap: 12px;
}

.stock-info .industry,
.stock-info .area {
  color: #7f8c8d;
  font-size: 0.9rem;
  background-color: #f0f0f0;
  padding: 4px 8px;
  border-radius: 12px;
}

.stock-market {
  display: flex;
  align-items: center;
}

.stock-market .market {
  color: #7f8c8d;
  font-size: 0.9rem;
  background-color: #f0f0f0;
  padding: 4px 8px;
  border-radius: 12px;
}

/* 股票详情 */
.stock-detail {
  margin-top: 40px;
}

.stock-detail h2 {
  font-size: 2rem;
  color: #2c3e50;
  margin-bottom: 20px;
  text-align: center;
}

.basic-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.label {
  font-weight: bold;
  color: #7f8c8d;
  margin-bottom: 5px;
}

.value {
  color: #2c3e50;
  font-size: 1.1rem;
}

/* 图表部分 */
.chart-section {
  margin-bottom: 40px;
}

.chart-section h3 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin-bottom: 15px;
}

.chart-controls {
  margin-bottom: 20px;
}

.chart-description {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #3498db;
}

.chart-description p {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-weight: bold;
}

.chart-description ul {
  margin: 0;
  padding-left: 20px;
}

.chart-description li {
  margin-bottom: 5px;
  color: #34495e;
  font-size: 0.9rem;
}

.period-btn {
  padding: 8px 16px;
  margin-right: 10px;
  border: 1px solid #e0e0e0;
  background-color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.period-btn.active {
  background-color: #3498db;
  color: white;
  border-color: #3498db;
}

.chart-container {
  height: 800px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.default-chart-section {
  margin-bottom: 40px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
}

.default-chart-section h2 {
  font-size: 1.8rem;
  color: #2c3e50;
  margin-bottom: 20px;
  text-align: center;
}

/* 技术指标 */
.indicators-section {
  margin-bottom: 40px;
}

.indicators-section h3 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin-bottom: 20px;
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.indicator-card {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  text-align: center;
}

.indicator-name {
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 10px;
}

.indicator-value {
  font-size: 1.2rem;
  color: #34495e;
  margin-bottom: 10px;
}

.indicator-status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: bold;
}

.indicator-status.positive {
  background-color: rgba(46, 204, 113, 0.2);
  color: #2ecc71;
}

.indicator-status.negative {
  background-color: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.indicator-status.overbought {
  background-color: rgba(243, 156, 18, 0.2);
  color: #f39c12;
}

.indicator-status.oversold {
  background-color: rgba(52, 152, 219, 0.2);
  color: #3498db;
}

.indicator-status.normal {
  background-color: rgba(46, 204, 113, 0.2);
  color: #2ecc71;
}

/* 诊断结果 */
.diagnosis-section {
  margin-bottom: 40px;
}

.diagnosis-section h3 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin-bottom: 20px;
}

.diagnosis-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.score-card {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  text-align: center;
}

.score-card.overall {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.score-card.technical {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.score-card.fundamental {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.score-title {
  font-size: 0.9rem;
  margin-bottom: 10px;
  opacity: 0.9;
}

.score-value {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.score-label {
  font-size: 0.8rem;
  opacity: 0.9;
}

.diagnosis-details {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  font-size: 1.2rem;
  color: #2c3e50;
  margin-bottom: 15px;
}

.detail-section ul {
  list-style: none;
  padding: 0;
}

.detail-section li {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  color: #34495e;
}

.detail-section li:last-child {
  border-bottom: none;
}

.recommendation {
  display: inline-block;
  padding: 8px 20px;
  border-radius: 20px;
  font-weight: bold;
  font-size: 1.1rem;
  margin-bottom: 15px;
}

.recommendation.buy {
  background-color: rgba(46, 204, 113, 0.2);
  color: #2ecc71;
}

.recommendation.hold {
  background-color: rgba(243, 156, 18, 0.2);
  color: #f39c12;
}

.recommendation.sell {
  background-color: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
}

.risk-level {
  color: #7f8c8d;
}

.risk-level .low-risk {
  color: #2ecc71;
  font-weight: bold;
}

.risk-level .medium-risk {
  color: #f39c12;
  font-weight: bold;
}

.risk-level .high-risk {
  color: #e74c3c;
  font-weight: bold;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stock-diagnosis {
    padding: 15px;
  }
  
  .index-grid {
    grid-template-columns: 1fr;
  }
  
  .search-box {
    flex-direction: column;
  }
  
  .basic-info {
    grid-template-columns: 1fr;
  }
  
  .indicators-grid {
    grid-template-columns: 1fr;
  }
  
  .diagnosis-summary {
    grid-template-columns: 1fr;
  }
  
  .chart-container {
    height: 600px;
  }
}
</style>
