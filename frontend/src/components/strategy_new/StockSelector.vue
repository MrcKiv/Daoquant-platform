<template>
  <div class="stock-selector">
    <h2 style="width: 800px; " class="title">选择策略</h2>

    <table class="strategy-table">
      <thead>
        <tr>
          <th>策略类别</th>
          <th>策略名称</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(c, i) in conditions" :key="i">
          <td>
            <select v-model="c.factor">
              <option value="基本策略">基本策略</option>
              <option value="深度学习策略">深度学习策略</option>
            </select>
          </td>
          <td>
            <select v-model="c.operator">
              <option>macd策略</option>
              <option>macd优化策略</option>
              <option>macd行业策略</option>
              <option>macd概念策略</option>
              <option>sby策略</option>
              <option>hbb策略</option>
              <option>cmy策略</option>
              <option>日线与60分钟金叉匹配策略</option>
              <option>日线与60分钟金叉匹配自动交易策略</option>
              <option>Mark策略</option>
              <option>ARIMA_AIC</option>
              <option>深度学习RL策略</option>
            </select>
          </td>
          <td>
            <button @click="removeCondition(i)" class="btn-delete">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="button-group">
      <button @click="openModal" class="btn-primary">选择策略</button>
      <button @click="saveForm" class="btn-save">保存</button>
    </div>

    <!-- 模态框 -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h3 class="modal-title">选择策略</h3>

        <div class="form-group">
          <label>策略类别：</label>
          <select v-model="selectedFactor">
            <option value="基本策略">基本策略</option>
            <option value="深度学习策略">深度学习策略</option>
          </select>
        </div>

        <div class="form-group">
          <label>策略名称：</label>
          <select v-model="selectedOperator">
            <option>macd策略</option>
              <option>行业策略</option>
              <option>深度学习策略</option>
              <option>日线与60分钟金叉匹配自动交易策略</option>
              <option>Mark策略</option>
              <option>ARIMA_AIC</option>
              <option>深度学习RL策略</option>
          </select>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn-cancel">取消</button>
          <button @click="confirmSelection" class="btn-confirm">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import {useRoute} from "vue-router";  // 引入 axios
const route = useRoute()
const strategyName = route.params.id
// 表格数据
const conditions = ref([
  { factor: '基本策略', operator: 'Mark策略' }
])

// 模态框控制
const showModal = ref(false)
const selectedFactor = ref('基本策略')
const selectedOperator = ref('Mark策略')

// 打开模态框
const openModal = () => {
  showModal.value = true
}

// 关闭模态框
const closeModal = () => {
  showModal.value = false
}

// 添加新策略
const confirmSelection = () => {
  conditions.value.push({
    factor: selectedFactor.value,
    operator: selectedOperator.value
  })
  closeModal()
}

// 删除行
const removeCondition = (index) => {
  conditions.value.splice(index, 1)
}

const emit = defineEmits(['update:selector'])
// 保存表单 - 发送 Ajax 请求
const saveForm = async () => {
  const payload = {
    strategyName: strategyName,
    conditions: conditions.value
  }

  try {
    const response = await axios.post('/api/strategy/getStockSelector/', payload)
     emit('update:selector', response.data) // 发送选股器数据
    console.log('提交成功:', response.data)
    alert('策略已保存！')
  } catch (error) {
    console.error('提交失败:', error)
    alert('保存策略失败，请重试。')
  }
}
</script>


<style scoped>
.stock-selector {
  padding: 20px;
  font-family: Arial, sans-serif;
}

.title {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 20px;
}

.strategy-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

.strategy-table thead {
  background-color: #f2f2f2;
}

.strategy-table th,
.strategy-table td {
  border: 1px solid #ccc;
  text-align: center;
  padding: 10px;
}

.strategy-table select {
  width: 100%;
  padding: 5px;
  border-radius: 4px;
  border: 1px solid #999;
}

.button-group {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.btn-primary,
.btn-save,
.btn-delete {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
  font-weight: bold;
}

.btn-primary {
  background-color: #4caf50;
}

.btn-save {
  background-color: #2196f3;
}

.btn-delete {
  background-color: #f44336;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 320px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  animation: fadeInUp 0.3s ease-in-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 15px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.form-group select {
  width: 100%;
  padding: 6px;
  border: 1px solid #999;
  border-radius: 4px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-cancel,
.btn-confirm {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.btn-cancel {
  background-color: #ccc;
}

.btn-confirm {
  background-color: #2196f3;
  color: white;
}
</style>
