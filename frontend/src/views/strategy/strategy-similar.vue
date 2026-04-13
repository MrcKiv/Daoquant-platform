<template>
  <div class="page-container">
    <!-- 条件筛选区域 -->
    <el-row :gutter="20" class="filter-area" align="middle">
      <el-col :span="6">
        <el-input v-model="queryParams.code" placeholder="请输入股票代码" clearable />
      </el-col>
      <el-col :span="6">
        <el-date-picker
          v-model="queryParams.startDate"
          type="date"
          placeholder="选择开始日期"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-col>
      <el-col :span="6">
        <el-date-picker
          v-model="queryParams.endDate"
          type="date"
          placeholder="选择结束日期"
          value-format="YYYY-MM-DD"
          style="width: 100%"
        />
      </el-col>
      <el-col :span="6">
        <el-button type="primary" style="width: 100%" @click="handleSearch">查询</el-button>
      </el-col>
    </el-row>

    <!-- 图表对比区域 -->
    <div class="charts-comparison-area">
      <!-- 主K线图 -->
      <div class="chart-panel">
        <div class="chart-container" v-loading="loadingBase">
          <div class="chart-header">
            <div class="chart-title">{{ baseStock.code || '基准股票' }} K线图</div>
          </div>
          <div class="chart-body" :ref="setMainChartRef"></div>
        </div>
      </div>

      <!-- 对比K线图 -->
      <div class="chart-panel">
        <div class="chart-container" v-loading="loadingDetail">
          <div class="chart-header">
            <div class="chart-title">
              {{ selectedStock?.code ? `${selectedStock.code} 对比图` : '请选择对比股票' }}
            </div>
            <el-button
              v-if="drawerVisible"
              type="danger"
              size="small"
              @click="closeDetail"
            >
              关闭对比
            </el-button>
          </div>
          <div
            ref="detailChartRef"
            class="chart-body"
            :class="{ 'chart-placeholder': !drawerVisible }"
          >
            <div v-if="!drawerVisible" class="placeholder-text">
              请从下方列表选择股票进行对比
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 相似股票列表 -->
    <div class="similar-list-area">
      <el-table
        :data="similarStocks"
        stripe
        highlight-current-row
        @row-click="handleRowClick"
        height="300"
      >
        <el-table-column prop="code" label="股票代码" width="120" />
        <el-table-column prop="startDate" label="起始日期" width="150" />
        <el-table-column prop="endDate" label="终止日期" width="150" />
        <el-table-column prop="similarity" label="相似度" width="120">
          <template #default="{ row }">
            <el-tag :type="getSimilarityTagType(row?.similarity)">
              {{ (row?.similarity * 100).toFixed(2) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="windowSize" label="窗口大小" width="120" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" @click="showDetail(row)">对比查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useKlineChart } from '@/stores/useKlineChart'

const mainChartRef = ref(null)
const detailChartRef = ref(null)

const baseStock = reactive({ code: '', data: null })
const similarStocks = ref([])
const loadingBase = ref(false)
const loadingSimilar = ref(false)
const loadingDetail = ref(false)
const drawerVisible = ref(false)
const selectedStock = ref(null)

const queryParams = reactive({
  code: '',
  startDate: '',
  endDate: ''
})

// 函数式 ref 绑定，确保可用
function setMainChartRef(el) {
  if (!el) return
  mainChartRef.value = el

  // 容器高度判断确保初始化成功
  const waitUntilReady = setInterval(() => {
    if (el.offsetHeight > 0 && el.offsetWidth > 0 && baseStock.data?.dates?.length) {
      clearInterval(waitUntilReady)
      console.log('✅ chart ref 尺寸就绪:', el.offsetWidth, el.offsetHeight)
      // useKlineChart(mainChartRef, baseStock.data, '基准股票')
    }
  }, 100)
}

const fetchBaseData = async () => {
  try {
    loadingBase.value = true
    const res = await axios.get('/api/strategy/getBase/', {
      params: {
        code: queryParams.code,
        startDate: queryParams.startDate,
        endDate: queryParams.endDate
      }
    })
    baseStock.code = res.data.code
    baseStock.data = res.data.data
    console.log('📦 baseStock.data 加载成功:', baseStock.data)
    // 数据加载完成后，确保 DOM 已经准备好再绘制图表
    if (mainChartRef.value && baseStock.data?.dates?.length) {
      useKlineChart(mainChartRef, baseStock.data, '基准股票');
    }
  } catch (error) {
    console.error('加载基准数据失败:', error.response?.data || error.message)
    ElMessage.error('基准数据加载失败')
  } finally {
    loadingBase.value = false
  }
}

const fetchSimilarStocks = async () => {
  try {
    loadingSimilar.value = true
    const res = await axios.get('/api/strategy/getSimilar/', {
      params: {
        code: queryParams.code,
        startDate: queryParams.startDate,
        endDate: queryParams.endDate
      }
    })
    similarStocks.value = res.data.list.sort((a, b) => b.similarity - a.similarity)
  } catch (error) {
    console.error('加载相似股票失败:', error.response?.data || error.message)
    ElMessage.error('相似股票加载失败')
  } finally {
    loadingSimilar.value = false
  }
}

const handleSearch = () => {
  fetchBaseData()
  fetchSimilarStocks()
}

const showDetail = async (row) => {
  selectedStock.value = row
  drawerVisible.value = true
  loadingDetail.value = true
  try {
    const res = await axios.get('/api/strategy/getBase/', {
      params: {
        code: row.code,
        startDate: row.startDate,
        endDate: row.endDate
      }
    })
    const chartData = res.data.data
    console.log('chartData:', chartData)

    // 等待DOM更新后再绘制图表
    setTimeout(() => {
      if (detailChartRef.value) {
        useKlineChart(detailChartRef, chartData, `${row.code} K线图`)
      }
      loadingDetail.value = false
    }, 100)
  } catch (error) {
    ElMessage.error('加载详情失败')
    console.error(error)
    loadingDetail.value = false
  }
}

const closeDetail = () => {
  drawerVisible.value = false
  selectedStock.value = null
  // 清空对比图表
  if (detailChartRef.value) {
    detailChartRef.value.innerHTML = '<div class="placeholder-text">请从下方列表选择股票进行对比</div>'
  }
}

const getSimilarityTagType = (similarity) => {
  if (!similarity) return 'info'
  if (similarity > 0.9) return 'success'
  if (similarity > 0.8) return 'warning'
  return 'danger'
}

const handleRowClick = (row) => {
  console.log('点击行:', row)
  showDetail(row)
}

onMounted(() => {
  fetchBaseData()
  fetchSimilarStocks()
})
</script>

<style scoped lang="scss">
.page-container {
  padding: 20px;
  max-width: 100%;
  margin: 0 auto;

  .filter-area {
    margin-bottom: 20px;
    padding: 20px;
    background: #f9f9fb;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  }

  .charts-comparison-area {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
    height: 500px;

    .chart-panel {
      .chart-container {
        border: 1px solid #ebeef5;
        border-radius: 4px;
        padding: 15px;
        height: 100%;
        display: flex;
        flex-direction: column;

        .chart-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;

          .chart-title {
            font-size: 16px;
            font-weight: bold;
            color: #303133;
          }
        }

        .chart-body {
          flex: 1;
          min-height: 0; // 允许收缩

          &.chart-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #fafafa;
            border-radius: 4px;

            .placeholder-text {
              color: #909399;
              font-size: 14px;
            }
          }
        }
      }
    }
  }

  .similar-list-area {
    border: 1px solid #ebeef5;
    border-radius: 4px;
    padding: 15px;

    :deep(.el-table__row) {
      cursor: pointer;
      &:hover {
        background-color: #f5f7fa;
      }
    }
  }
}
</style>
