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
<!--    <div style="margin-bottom: 15px;">-->
<!--      <label>-->
<!--        <input type="checkbox" v-model="excludeST" class="form-check-input" style="margin-top: 3px; width: 16px; height: 16px;">-->
<!--        剔除ST股票-->
<!--      </label>-->
<!--      &nbsp;&nbsp;&nbsp;-->
<!--      <label>-->
<!--        <input type="checkbox" v-model="excludeSuspended" class="form-check-input" style="margin-top: 3px; width: 16px; height: 16px;">-->
<!--        剔除停牌股票-->
<!--      </label>-->
<!--    </div>-->

    <div>
      <label style="display: block; margin-bottom: 8px; font-weight: bold;">标签筛选：</label>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
        <div v-for="item in stockLabels" :key="item.key" style="display: flex; align-items: center;">
          <input
            type="checkbox"
            :id="'label_' + item.key"
            :value="item.key"
            :checked="selectedLabels.includes(item.key)"
            @change="toggleLabel(item.key)"
            class="form-check-input"
            style="margin-top: 3px; width: 16px; height: 16px; margin-right: 5px;">
          <label :for="'label_' + item.key" style="margin-bottom: 0;">{{ item.label }}</label>
        </div>
      </div>
    </div>
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

// 添加标签列表（中英文对照）
const stockLabels = [
  { key: 'new_high_label', label: '创新高标签' },
  { key: 'new_low_label', label: '创新低标签' },
  { key: 'strong_year_label', label: '年线强势股' },
  { key: 'volatility_H', label: '高波动' },
  { key: 'MACD', label: 'MACD指标' },
  { key: 'MACD_Red_ratio_H', label: 'MACD红柱占比高' },
  { key: 'KDJ_H', label: 'KDJ高位' },
  { key: 'KDJ_L', label: 'KDJ低位' },
  { key: 'CCI_Overbuying', label: 'CCI超买' },
  { key: 'WR_Overbuying', label: '威廉指标超买' },
  { key: 'Up_200', label: '上涨200天' },
  { key: 'Consecutive_days__increase', label: '连续上涨天数' },
  { key: '5_day_increase', label: '5日上涨' },
  { key: '5_day_increase_rate', label: '5日上涨幅度' },
  { key: 'Annualized_income', label: '年化收益' },
  { key: 'CCI_Oversold', label: 'CCI超卖' },
  { key: 'WR_Oversold', label: '威廉指标超卖' },
  { key: 'fall_200', label: '下跌200天' },
  { key: 'Days_of_decline', label: '连续下跌天数' },
  { key: 'Annualized_volatility', label: '年化波动率' }
]

// 存储选中的标签
const selectedLabels = ref([])

// 处理标签选择变化
const toggleLabel = (key) => {
  const index = selectedLabels.value.indexOf(key)
  if (index > -1) {
    selectedLabels.value.splice(index, 1)
  } else {
    selectedLabels.value.push(key)
  }
}

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
    exclude_suspended: excludeSuspended.value,
     labels: selectedLabels.value
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
        const res = await axios.post('/api/strategy/loadStrategySummary/', {
          strategyName: strategyName
        }, {
          withCredentials: true
        })
        console.log('完整返回数据:', res.data);
        if (res.data && (res.data.success === true || res.data.received_data)) {
          console.log('加载策略成功:', res.data.received_data)
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
          console.log('加载策略配置:', {
            capital: capital.value,
            ratio: ratio.value,
            hold: hold.value,
            benchmark: benchmark.value,
            startDate: startDate.value,
            endDate: endDate.value,
            scope: scope.value,
            stampTax: stampTax.value,
            fee: fee.value,
            commission: commission.value,
            minCommission: minCommission.value,
            excludeST: excludeST.value,
            excludeSuspended: excludeSuspended.value
          })
          // 加载标签数据
          if (data.labels) {
            console.log('加载标签数据:', data.labels)
            selectedLabels.value = data.labels
          }
        } else {
          const errorMessage = res.data.message || res.data.error || '未知错误'
          res.data.message = errorMessage
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
