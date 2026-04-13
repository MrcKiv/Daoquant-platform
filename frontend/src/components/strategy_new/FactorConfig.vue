<template>
  <div class="stock-selector">
    <h2 style="width: 800px;" class="title">因子配置</h2>

    <!-- 策略类型选择 -->
    <div class="strategy-type-selector">
      <label>
        <input
          type="radio"
          v-model="strategyType"
          value="static"
          @change="onStrategyTypeChange"
        >
        静态止盈止损策略
      </label>
      <label>
        <input
          type="radio"
          v-model="strategyType"
          value="dynamic"
          @change="onStrategyTypeChange"
        >
        动态止盈止损策略
      </label>
    </div>

    <!-- 静态因子配置 (兜底因子配置) -->
    <div v-show="strategyType === 'static'">
      <h3>静态因子配置</h3>
      <table class="strategy-table">
        <thead>
          <tr>
            <th>因子名称</th>
            <th>比较符</th>
            <th>值</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(g, j) in fallbackFactors" :key="j">
            <td>{{ g.name }}</td>
            <td>
              <select v-model="g.operator">
                <option>大于</option>
                <option>等于</option>
                <option>小于</option>
              </select>
            </td>
            <td><input type="number" v-model.number="g.value" /></td>
            <td><button @click="removeFallback(j)" class="btn-delete">删除</button></td>
          </tr>
        </tbody>
      </table>

      <div class="button-group">
        <button @click="openStaticModal" class="btn-primary">+ 添加静态因子</button>
        <button @click="saveForm" class="btn-save">保存</button>
      </div>
    </div>

    <!-- 动态因子配置 -->
    <div v-show="strategyType === 'dynamic'">
      <h3>动态因子配置</h3>
      <table class="strategy-table">
        <thead>
          <tr>
            <th>因子名称</th>
            <th>值</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(g, j) in dynamicFactors" :key="j">
            <td>{{ g.name }}</td>
            <td><input type="number" v-model.number="g.value" /></td>
            <td><button @click="removeDynamic(j)" class="btn-delete">删除</button></td>
          </tr>
        </tbody>
      </table>

      <div class="button-group">
        <button @click="openDynamicModal" class="btn-primary">+ 添加动态因子</button>
        <button @click="saveForm" class="btn-save">保存</button>
      </div>
    </div>

    <!-- 静态因子模态框 -->
    <div v-if="showStaticModal" class="modal-overlay" @click.self="closeStaticModal">
      <div class="modal">
        <h3 class="modal-title">添加静态因子</h3>

        <div class="form-group">
          <label>因子名称：</label>
          <select v-model="newStaticFactor.name">
            <option value="" disabled selected>请选择因子名称</option>
            <option value="上涨幅度">上涨幅度</option>
            <option value="下跌幅度">下跌幅度</option>
            <option value="最大持股天数">最大持股天数</option>
          </select>
        </div>

        <div class="form-group">
          <label>比较符：</label>
          <select v-model="newStaticFactor.operator">
            <option>大于</option>
            <option>等于</option>
            <option>小于</option>
          </select>
        </div>

        <div class="form-group">
          <label>值：</label>
          <input type="number" v-model.number="newStaticFactor.value" placeholder="请输入数值" />
        </div>

        <div class="modal-footer">
          <button @click="closeStaticModal" class="btn-cancel">取消</button>
          <button @click="confirmAddStatic" class="btn-confirm">确认</button>
        </div>
      </div>
    </div>

    <!-- 动态因子模态框 -->
    <div v-if="showDynamicModal" class="modal-overlay" @click.self="closeDynamicModal">
      <div class="modal">
        <h3 class="modal-title">添加动态因子</h3>

        <div class="form-group">
          <label>因子名称：</label>
          <select v-model="newDynamicFactor.name">
            <option value="" disabled selected>请选择因子名称</option>
            <option value="动态止盈止损">动态止盈止损</option>
            <option value="波动率动态止盈止损">波动率动态止盈止损</option>
            <option value="相对强度卖出">相对强度卖出</option>
            <option value="技术趋势卖出">峰值回撤止损</option>
            <option value="技术趋势卖出">ATR波动率止损</option>
            <option value="技术趋势卖出">均线交叉退出</option>
            <option value="技术趋势卖出">时间衰减收紧止损</option>
            <option value="技术趋势卖出">利润锁仓保护</option>
            <option value="技术趋势卖出">波动率缩放止盈</option>
<!--            <option value="技术趋势卖出">技术趋势卖出</option>-->
          </select>
        </div>

        <div class="form-group">
          <label>值：</label>
          <input type="number" v-model.number="newDynamicFactor.value" placeholder="请输入数值" />
        </div>

        <div class="modal-footer">
          <button @click="closeDynamicModal" class="btn-cancel">取消</button>
          <button @click="confirmAddDynamic" class="btn-confirm">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import {useRoute} from "vue-router";

const route = useRoute()
const strategyName = route.params.id

// 策略类型：static(静态) 或 dynamic(动态)
const strategyType = ref('static')

// 静态因子配置
const fallbackFactors = ref([
  { name: '上涨幅度', operator: '大于', value: 5 },
  { name: '下跌幅度', operator: '大于', value: 2 },
  { name: '最大持股天数', operator: '大于', value: 5 }
])

// 动态因子配置
const dynamicFactors = ref([
  { name: '动态止盈止损', value: 1 },
  { name: '波动率动态止盈止损', value: 1 }
])

// 控制静态因子模态框
const showStaticModal = ref(false)
const newStaticFactor = ref({
  name: '',
  operator: '大于',
  value: 0
})

// 控制动态因子模态框
const showDynamicModal = ref(false)
const newDynamicFactor = ref({
  name: '',
  value: 1
})

// 策略类型改变时的处理
const onStrategyTypeChange = () => {
  // 可以在这里添加切换策略类型时的处理逻辑
  console.log('策略类型已切换为:', strategyType.value)
}

// 打开静态因子模态框
const openStaticModal = () => {
  showStaticModal.value = true
}

// 关闭静态因子模态框
const closeStaticModal = () => {
  showStaticModal.value = false
  newStaticFactor.value = { name: '', operator: '大于', value: 0 }
}

// 确认添加静态因子
const confirmAddStatic = () => {
  if (!newStaticFactor.value.name.trim()) return
  fallbackFactors.value.push({ ...newStaticFactor.value })
  closeStaticModal()
}

// 删除静态因子
const removeFallback = (index) => {
  fallbackFactors.value.splice(index, 1)
}

// 打开动态因子模态框
const openDynamicModal = () => {
  showDynamicModal.value = true
}

// 关闭动态因子模态框
const closeDynamicModal = () => {
  showDynamicModal.value = false
  newDynamicFactor.value = { name: '', value: 1 }
}

// 确认添加动态因子
const confirmAddDynamic = () => {
  if (!newDynamicFactor.value.name.trim()) return
  dynamicFactors.value.push({ ...newDynamicFactor.value })
  closeDynamicModal()
}

// 删除动态因子
const removeDynamic = (index) => {
  dynamicFactors.value.splice(index, 1)
}

const emit = defineEmits(['update:factor'])

// 保存表单 - 发送 Ajax 请求
const saveForm = async () => {
  let payloadFactors = [];

  // 根据策略类型选择发送的因子数据
  if (strategyType.value === 'static') {
    payloadFactors = fallbackFactors.value;
  } else {
    payloadFactors = dynamicFactors.value;
  }

  const payload = {
    strategyName: strategyName,
    strategyType: strategyType.value,
    factors: payloadFactors
  }

  try {
    const response = await axios.post('/api/strategy/getFactorConfig/', payload)
    console.log('提交成功:', response.data)
    // 触发事件，将数据传给父组件
    emit('update:factor', response.data) // 发送因子数据
    alert('因子配置已保存！')
  } catch (error) {
    console.error('提交失败:', error)
    alert('保存因子配置失败，请重试。')
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

.strategy-type-selector {
  margin-bottom: 20px;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.strategy-type-selector label {
  margin-right: 20px;
  font-weight: bold;
}

.strategy-type-selector input[type="radio"] {
  margin-right: 5px;
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

.strategy-table select,
.strategy-table input[type='number'] {
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

.form-group input,
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
