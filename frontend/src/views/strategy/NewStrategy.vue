<template>
  <div class="new-strategy-container">
    <!-- 新建按钮 -->
    <el-button type="primary" @click="dialogFormVisible = true" class="new-strategy-btn">新建</el-button>

    <!-- 策略列表表格 -->
    <el-table
      :data="strategies"
      style="width: 100%; margin-top: 20px;"
      border
      :default-sort="{ prop: 'strategyName', order: 'ascending' }"
    >
      <!-- 策略名称 -->
      <el-table-column prop="strategyName" label="策略名称" sortable  width="450">
        <template #default="scope">
          <span class="strategy-link" @click="goToStrategyDetail(scope.row)">
            {{ scope.row.strategyName }}
          </span>
        </template>
      </el-table-column>

      <!-- 开始日期 -->
      <el-table-column prop="start_date" label="开始日期" sortable />

      <!-- 结束日期 -->
      <el-table-column prop="end_date" label="结束日期" sortable />

      <!-- 初始资金 -->
      <el-table-column prop="init_fund" label="初始资金(万元)">
        <template #default="scope">
          {{ formatCurrency(scope.row.init_fund) }}
        </template>
      </el-table-column>

      <!-- 最大持仓数 -->
      <el-table-column prop="max_hold_num" label="最大持仓数" />

      <!-- 收益基准 -->
      <el-table-column prop="income_base" label="收益基准" />

      <!-- 剔除ST股 -->
      <el-table-column label="剔除ST股">
        <template #default="scope">
          {{ scope.row.remove_st_stock === 'true' ? '是' : '否' }}
        </template>
      </el-table-column>

      <!-- 剔除停牌股 -->
      <el-table-column label="剔除停牌股">
        <template #default="scope">
          {{ scope.row.remove_suspended_stok === 'true' ? '是' : '否' }}
        </template>
      </el-table-column>

      <!-- 操作 -->
      <el-table-column label="操作" width="100">
        <template #default="scope">
          <el-button size="small" type="danger" @click="handleDelete(scope.$index, scope.row)">删除</el-button>
        </template>
      </el-table-column>

      <!-- 公开 -->
      <el-table-column label="操作" width="100">
        <template #default="scope">
          <el-button size="small" type="primary" @click="handlePublic(scope.$index, scope.row)">公开</el-button>
        </template>
      </el-table-column>
    </el-table>


    <!-- 新建策略弹窗 -->
    <el-dialog v-model="dialogFormVisible" title="新建策略" width="40%">
      <el-form :model="form" label-width="120px">
        <el-form-item label="策略名称">
          <el-input v-model="form.name" autocomplete="off" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogFormVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCreate">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessageBox } from 'element-plus'


const router = useRouter()
const strategies = ref([])
const dialogFormVisible = ref(false)
const form = reactive({
  name: ''
})

// 格式化金额
const formatCurrency = (value) => {
  if (!value) return '0.00'
  return parseFloat(value).toLocaleString('zh-CN', {
    style: 'currency',
    currency: 'CNY'
  })
}

// 页面加载时获取策略数据
onMounted(async () => {
  try {
    const res = await axios.get('/api/strategy/newconstruction/', {
      withCredentials: true
    })

    strategies.value = res.data.state || []

    // 路由参数更新（可选）
    if (strategies.value.length > 0) {
      router.push({ query: { hasData: 'true' } })
    } else {
      router.push({ query: { hasData: 'false' } })
    }
  } catch (err) {
    console.error('获取策略失败:', err)
  }
})
// 公开策略
const handlePublic = async (index, row) => {
  try {
    // ✅ 确认是否要公开该策略
    await ElMessageBox.confirm(
      '确定要公开该策略吗？此操作不可撤销',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 更新策略的公开状态
    const res = await axios.post('/api/strategy/public_strategy/', {
      strategyName: row.strategyName,
      userID: row.userID // 假设这里有 userID 字段
    }, {
      withCredentials: true
    })

    if (res.data.success) {
      // 更新本地数据的状态
      strategies.value[index].is_public = true
      alert('公开成功')
    } else {
      alert('公开失败: ' + res.data.message)
    }
  } catch (err) {
    if (err.response && err.response.status === 400) {
      alert('请求错误: ' + err.response.data.message)
    } else {
      console.error('公开策略失败:', err)
      alert('网络错误，请重试')
    }
  }
}
// 新建策略
// 新建策略
const handleCreate = async () => {
  if (!form.name.trim()) {
    alert('策略名称不能为空')
    return
  }

  // ✅ 检查策略名称是否已存在
  const exists = strategies.value.some(s => s.strategyName === form.name)
  if (exists) {
    alert('策略名称已存在，请更换名称')
    return
  }

  try {
    const res = await axios.post('/api/strategy/insert_name/', {
      strategyName: form.name
    }, {
      withCredentials: true
    })

    if (res.data.success) {
      strategies.value.push({
        strategyName: form.name,
        start_date: '-',
        end_date: '-',
        init_fund: 0,
        max_hold_num: 0,
        income_base: '-',
        remove_st_stock: 'false',
        remove_suspended_stok: 'false'
      })

      alert('策略创建成功！')
      dialogFormVisible.value = false
      // form.name = ''
      router.push({
        name: 'StrategyConfig',  // 确保你的路由中定义了 name: 'StrategyConfig'
        params: { id: form.name }
      })
    } else {
      alert('创建策略失败: ' + res.data.message)
    }
  } catch (err) {
    console.error('创建策略失败:', err)
    alert('网络错误，请重试')
  }
}


// 删除策略
const handleDelete = async (index, row) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除该策略吗？此操作不可撤销',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await axios.post('/api/strategy/delete_strategy/', {
      strategyName: row.strategyName
    }, {
      withCredentials: true
    })

    if (res.data.success) {
      // ✅ 使用策略名称查找索引
      const idx = strategies.value.findIndex(s => s.strategyName === row.strategyName)
      if (idx > -1) {
        strategies.value.splice(idx, 1)
      }
      alert('删除成功')
    } else {
      alert('删除失败: ' + res.data.message)
    }
  } catch (err) {
    if (err.response && err.response.status === 400) {
      alert('请求错误: ' + err.response.data.message)
    } else {
      console.error('删除策略失败:', err)
      alert('网络错误，请重试')
    }
  }
}



// 跳转到策略详情页
const goToStrategyDetail = (row) => {
  router.push({
    name: 'StrategyDetail',
    params: { id: row.strategyName }
  })
}
</script>

<style scoped>
.new-strategy-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.new-strategy-btn {
  margin-bottom: 20px;
}

.strategy-link {
  color: #409EFF;
  cursor: pointer;
  text-decoration: underline;
}

.strategy-link:hover {
  color: #337ecc;
}

.el-table {
  --el-table-row-height: 60px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

.el-table-column {
  font-size: 16px;
}

.el-table th,
.el-table td {
  text-align: center;
}

.el-dialog {
  border-radius: 8px;
}

.el-form-item__label {
  font-weight: bold;
}
</style>
