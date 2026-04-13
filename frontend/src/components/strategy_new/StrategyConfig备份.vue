<template>

  <form class="strategy-form">
    <table class="config-table">
      <thead>
        <tr>
          <th>配置项</th>
          <th>参数设置</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>初始资金</td>
          <td>
            <input v-model="capital" style="width: 150px;" placeholder="单位：万元" />万元

          </td>
        </tr>
        <tr>
          <td>投资比例</td>
          <td>
            <input v-model="ratio" style="width: 150px;" placeholder="百分比" />
            %
          </td>
        </tr>
        <tr>
          <td>持股数目</td>
          <td>
            <input v-model="hold" style="width: 150px;" placeholder="如 10" />
            只
          </td>
        </tr>
        <tr>
          <td>收益基准</td>
          <td>
            <select v-model="benchmark">
              <option value="沪深300">沪深300</option>
              <option value="上证50">上证50</option>
            </select>
          </td>
        </tr>
        <tr>
          <td>选择日期</td>
          <td>
            <input type="date" style="width: 160px;" v-model="startDate" />
            <span style="margin: 0 8px;">至</span>
            <input type="date" style="width: 160px;" v-model="endDate" />
          </td>
        </tr>
        <tr>
          <td>选股范围</td>
          <td>
            <select style="width: 150px;" v-model="scope">
              <option value="全部">全部</option>
              <option value="沪深A股">沪深A股</option>
            </select>
          </td>
        </tr>
        <tr>
          <td>费率设置</td>
          <td>
            <label>印花税：</label>
            <input type="text" v-model="stampTax" style="width: 50px;" placeholder="请输入"> %
            &nbsp;&nbsp;
            <label>过户费：</label>
            <input type="text" v-model="fee" style="width: 50px;" placeholder="请输入"> %
            &nbsp;&nbsp;
            <label>佣金：</label>
            <input type="text" v-model="commission" style="width: 50px;" placeholder="请输入"> %
            &nbsp;&nbsp;
            <label>最低佣金：</label>
            <input type="text" v-model="minCommission" style="width: 50px;" placeholder="请输入"> 元
          </td>
        </tr>
        <tr>
          <td>其他设置</td>
          <td>
            <label>
              <input type="checkbox" v-model="excludeST" class="form-check-input" style="margin-top: 3px; width: 16px; height: 16px;">
              剔除ST股票
            </label>
            &nbsp;&nbsp;&nbsp;
            <label>
              <input type="checkbox" v-model="excludeSuspended" class="form-check-input" style="margin-top: 3px; width: 16px; height: 16px;">
              剔除停牌股票
            </label>
          </td>
        </tr>
      </tbody>
    </table>

    <div style="text-align: center; margin-top: 24px;">
      <button type="submit" @click.prevent="submit">保存</button>
    </div>

  </form>
</template>

<script setup>
import {onMounted, ref} from 'vue'
import axios from 'axios'  // 引入 axios

const capital = ref(100)
const ratio = ref(100)
const hold = ref(10)
const benchmark = ref('沪深300')
const startDate = ref('')
const endDate = ref('')
const scope = ref('全部')
const stampTax = ref('1') // 印花税，默认值 1‰
const fee = ref('0.02') // 过户费，默认值 0.02‰
const commission = ref('0.25') // 佣金，默认值 0.25‰
const minCommission = ref('5') // 最低佣金，默认值 5元

const excludeST = ref(false) // 是否剔除 ST 股票
const excludeSuspended = ref(false) // 是否剔除停牌股票
import { useRoute } from 'vue-router'
const route = useRoute()
const strategyName = route.params.id

const emit = defineEmits(['update:strategy'])
const submit = async () => {
  const configData = {
     strategyName: strategyName,
    capital: capital.value,
    ratio: ratio.value,
    hold: hold.value,
    benchmark: benchmark.value,
    start_date: startDate.value,
    end_date: endDate.value,
    scope: scope.value,
    stamp_tax: stampTax.value,
    fee: fee.value,
    commission: commission.value,
    min_commission: minCommission.value,
    exclude_st: excludeST.value,
    exclude_suspended: excludeSuspended.value
  }



  try {

    const response = await axios.post('/api/strategy/getStrategyConfig/', configData)
     emit('update:strategy', configData) // 发送策略数据
    console.log('保存成功:', response.data)
    console.log('strategyName:', strategyName)
    alert('策略保存成功！')
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存策略失败，请重试。')
  }
}
const loadStrategyConfig = async () => {
      try {
        const res = await axios.post('/api/strategy/loadStrategyConfig/', {
          strategyName: strategyName
        }, {
          withCredentials: true
        })

        if (res.data.success) {
          const data = res.data.received_data

          // 填充表单数据
          capital.value = data.capital
          ratio.value = data.ratio
          hold.value = data.hold
          benchmark.value = data.benchmark
          startDate.value = data.start_date
          endDate.value = data.end_date
          scope.value = data.scope
          stampTax.value = data.stamp_tax
          fee.value = data.fee
          commission.value = data.commission
          minCommission.value = data.min_commission
          excludeST.value = data.exclude_st
          excludeSuspended.value = data.exclude_suspended
        } else {
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
</script>


<style scoped>
.strategy-form {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.config-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.config-table th,
.config-table td {
  border: 1px solid #e4e4e4;
  padding: 12px 16px;
  text-align: left;
  vertical-align: middle;
}

.config-table th {
  background-color: #f9fafb;
  font-weight: bold;
  color: #333;
}

.config-table input,
.config-table select {
  padding: 6px 10px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 6px;
  width: 100%;
  box-sizing: border-box;
}

.config-table select {
  height: 32px;
}

.config-table button {
  padding: 10px 20px;
  background: #0055cc;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.config-table button:hover {
  background: #003f99;
}
</style>
