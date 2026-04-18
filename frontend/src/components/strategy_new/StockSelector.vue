<template>
  <div class="stock-selector">
    <h2 class="title">选择策略</h2>

    <section class="upload-panel">
      <div class="upload-copy">
        <h3>上传自定义策略</h3>
        <p>支持上传 `.py` 文件。文件中需包含 `strategy_main`、`my_strategy_main`、`main`、`run` 之一作为入口函数。</p>
        <p>入口函数签名需与系统回测入口保持一致：`(Init_fund, Investment_ratio, Hold_stock_num, Start_time, End_time, Optionfacname, Botfacname, sid, uid)`。</p>
      </div>
      <div class="upload-actions">
        <input
          ref="fileInputRef"
          class="hidden-input"
          type="file"
          accept=".py"
          @change="handleStrategyFileChange"
        >
        <a
          class="btn-template"
          :href="templateDownloadUrl"
          download="daoquant_strategy_template.py"
        >
          下载模板
        </a>
        <button class="btn-upload" :disabled="isUploading" @click="triggerUpload">
          {{ isUploading ? '上传中...' : '上传策略' }}
        </button>
        <button class="btn-refresh" :disabled="isUploading" @click="fetchUploadedStrategies">
          刷新列表
        </button>
      </div>
    </section>

    <section class="uploaded-panel">
      <div class="uploaded-header">
        <h3>已上传策略</h3>
        <span class="uploaded-count">{{ uploadedStrategies.length }} 个</span>
      </div>
      <div v-if="uploadedStrategies.length" class="uploaded-list">
        <div v-for="item in uploadedStrategies" :key="item.id" class="uploaded-item">
          <div class="uploaded-info">
            <div class="uploaded-name">{{ item.name }}</div>
            <div class="uploaded-meta">
              {{ item.fileName }} · 入口 {{ item.entryFunction }}
            </div>
          </div>
          <button class="btn-add-custom" @click="appendUploadedStrategy(item)">加入选择</button>
        </div>
      </div>
      <div v-else class="uploaded-empty">当前还没有上传的自定义策略。</div>
    </section>

    <table class="strategy-table">
      <thead>
        <tr>
          <th>策略类别</th>
          <th>策略名称</th>
          <th>附加信息</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(condition, index) in conditions" :key="`${condition.factor}-${condition.operator}-${index}`">
          <td>
            <select v-model="condition.factor" @change="handleFactorChange(condition)">
              <option v-for="factor in strategyFactors" :key="factor" :value="factor">{{ factor }}</option>
            </select>
          </td>
          <td>
            <select v-model="condition.operator" @change="syncConditionWithOption(condition)">
              <option
                v-for="option in optionsForFactor(condition.factor)"
                :key="`${option.factor}-${option.operator}-${option.customStrategyId || 'builtin'}`"
                :value="option.operator"
              >
                {{ option.label }}
              </option>
            </select>
          </td>
          <td class="extra-cell">
            <span v-if="condition.strategySource === 'uploaded'">
              自定义策略
              <span v-if="condition.entryFunction">· 入口 {{ condition.entryFunction }}</span>
            </span>
            <span v-else>内置策略</span>
          </td>
          <td>
            <button class="btn-delete" @click="removeCondition(index)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="button-group">
      <button class="btn-primary" @click="openModal">选择策略</button>
      <button class="btn-save" @click="saveForm">保存</button>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h3 class="modal-title">选择策略</h3>

        <div class="form-group">
          <label>策略类别：</label>
          <select v-model="selectedFactor" @change="handleSelectedFactorChange">
            <option v-for="factor in strategyFactors" :key="factor" :value="factor">{{ factor }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>策略名称：</label>
          <select v-model="selectedOperator">
            <option
              v-for="option in selectedFactorOptions"
              :key="`${option.factor}-${option.operator}-${option.customStrategyId || 'builtin'}`"
              :value="option.operator"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="closeModal">取消</button>
          <button class="btn-confirm" @click="confirmSelection">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

const route = useRoute()
const strategyName = route.params.id

const BUILTIN_STRATEGIES = [
  { factor: '基本策略', operator: 'macd策略', label: 'macd策略' },
  { factor: '基本策略', operator: 'macd优化策略', label: 'macd优化策略' },
  { factor: '基本策略', operator: 'macd行业策略', label: 'macd行业策略' },
  { factor: '基本策略', operator: 'macd概念策略', label: 'macd概念策略' },
  { factor: '基本策略', operator: 'sby策略', label: 'sby策略' },
  { factor: '基本策略', operator: 'hbb策略', label: 'hbb策略' },
  { factor: '基本策略', operator: 'cmy策略', label: 'cmy策略' },
  { factor: '基本策略', operator: '日线与60分钟金叉匹配策略', label: '日线与60分钟金叉匹配策略' },
  { factor: '基本策略', operator: '日线与60分钟金叉匹配自动交易策略', label: '日线与60分钟金叉匹配自动交易策略' },
  { factor: '基本策略', operator: 'Mark策略', label: 'Mark策略' },
  { factor: '基本策略', operator: 'ARIMA_AIC', label: 'ARIMA_AIC' },
  { factor: '深度学习策略', operator: '深度学习RL策略', label: '深度学习RL策略' },
]

const fileInputRef = ref(null)
const showModal = ref(false)
const isUploading = ref(false)
const uploadedStrategies = ref([])
const selectedFactor = ref('基本策略')
const selectedOperator = ref('Mark策略')
const emit = defineEmits(['update:selector'])
const templateDownloadUrl = '/downloads/daoquant_strategy_template.py'

const buildUploadedOption = strategy => ({
  factor: '自定义策略',
  operator: strategy.name,
  label: strategy.name,
  strategySource: 'uploaded',
  customStrategyId: strategy.id,
  entryFunction: strategy.entryFunction,
  fileName: strategy.fileName,
})

const allStrategyOptions = computed(() => [
  ...BUILTIN_STRATEGIES.map(item => ({ ...item, strategySource: 'builtin', customStrategyId: null, entryFunction: null })),
  ...uploadedStrategies.value.map(buildUploadedOption),
])

const strategyFactors = computed(() => ['基本策略', '深度学习策略', '自定义策略'])

const strategyOptionsByFactor = computed(() => {
  const grouped = {
    基本策略: [],
    深度学习策略: [],
    自定义策略: [],
  }

  allStrategyOptions.value.forEach(option => {
    if (!grouped[option.factor]) {
      grouped[option.factor] = []
    }
    grouped[option.factor].push(option)
  })

  return grouped
})

const selectedFactorOptions = computed(() => optionsForFactor(selectedFactor.value))

const parseMaybeJson = value => {
  if (value == null || value === '') return []
  if (Array.isArray(value)) return value
  try {
    return JSON.parse(value)
  } catch {
    try {
      return JSON.parse(String(value).replace(/'/g, '"'))
    } catch {
      return []
    }
  }
}

const optionsForFactor = factor => strategyOptionsByFactor.value[factor] || []

const findStrategyOption = (factor, operator, customStrategyId = null) => {
  return optionsForFactor(factor).find(option => {
    if (customStrategyId && option.customStrategyId) {
      return option.customStrategyId === customStrategyId
    }
    return option.operator === operator
  })
}

const normalizeCondition = condition => {
  const normalized = {
    factor: condition?.factor || '基本策略',
    operator: condition?.operator || '',
    strategySource: condition?.strategySource || (condition?.factor === '自定义策略' || condition?.customStrategyId ? 'uploaded' : 'builtin'),
    customStrategyId: condition?.customStrategyId || condition?.custom_strategy_id || null,
    entryFunction: condition?.entryFunction || null,
  }

  const matchedOption = findStrategyOption(normalized.factor, normalized.operator, normalized.customStrategyId)
  if (matchedOption) {
    return {
      factor: matchedOption.factor,
      operator: matchedOption.operator,
      strategySource: matchedOption.strategySource,
      customStrategyId: matchedOption.customStrategyId || null,
      entryFunction: matchedOption.entryFunction || null,
    }
  }

  const fallbackOption = optionsForFactor(normalized.factor)[0]
  if (fallbackOption) {
    return {
      factor: fallbackOption.factor,
      operator: fallbackOption.operator,
      strategySource: fallbackOption.strategySource,
      customStrategyId: fallbackOption.customStrategyId || null,
      entryFunction: fallbackOption.entryFunction || null,
    }
  }

  return normalized
}

const defaultCondition = () => normalizeCondition(BUILTIN_STRATEGIES.find(item => item.operator === 'Mark策略') || BUILTIN_STRATEGIES[0])
const conditions = ref([defaultCondition()])

const syncConditionWithOption = condition => {
  Object.assign(condition, normalizeCondition(condition))
}

const handleFactorChange = condition => {
  const fallbackOption = optionsForFactor(condition.factor)[0]
  if (!fallbackOption) {
    condition.operator = ''
    condition.strategySource = condition.factor === '自定义策略' ? 'uploaded' : 'builtin'
    condition.customStrategyId = null
    condition.entryFunction = null
    return
  }

  Object.assign(condition, normalizeCondition(fallbackOption))
}

const handleSelectedFactorChange = () => {
  const firstOption = selectedFactorOptions.value[0]
  selectedOperator.value = firstOption?.operator || ''
}

const openModal = () => {
  handleSelectedFactorChange()
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

const confirmSelection = () => {
  const selectedOption = findStrategyOption(selectedFactor.value, selectedOperator.value)
  if (!selectedOption) {
    ElMessage.error('当前分类下没有可选策略')
    return
  }

  conditions.value.push(normalizeCondition(selectedOption))
  closeModal()
}

const removeCondition = index => {
  if (conditions.value.length === 1) {
    conditions.value = [defaultCondition()]
    return
  }
  conditions.value.splice(index, 1)
}

const triggerUpload = () => {
  fileInputRef.value?.click()
}

const fetchUploadedStrategies = async () => {
  try {
    const response = await axios.get('/api/strategy/listUploadedStrategies/', { withCredentials: true })
    uploadedStrategies.value = response.data?.strategies || []
    conditions.value = conditions.value.map(item => normalizeCondition(item))
    handleSelectedFactorChange()
  } catch (error) {
    console.error('fetchUploadedStrategies error:', error)
    ElMessage.error(error.response?.data?.error || '获取上传策略列表失败')
  }
}

const appendUploadedStrategy = strategy => {
  conditions.value.push(normalizeCondition(buildUploadedOption(strategy)))
}

const handleStrategyFileChange = async event => {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const formData = new FormData()
  formData.append('strategyFile', file)

  isUploading.value = true
  try {
    const response = await axios.post('/api/strategy/uploadStrategyFile/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      withCredentials: true,
    })

    const strategy = response.data?.strategy
    await fetchUploadedStrategies()
    if (strategy) {
      conditions.value.push(normalizeCondition(buildUploadedOption(strategy)))
    }
    ElMessage.success(response.data?.message || '策略上传成功')
  } catch (error) {
    console.error('handleStrategyFileChange error:', error)
    ElMessage.error(error.response?.data?.error || '上传策略失败')
  } finally {
    isUploading.value = false
  }
}

const loadSavedSelector = async () => {
  try {
    const response = await axios.post('/api/strategy/loadStrategySummary/', { strategyName }, { withCredentials: true })
    const rawConditions = parseMaybeJson(response.data?.backtest_config?.optionfactor)
    if (Array.isArray(rawConditions) && rawConditions.length > 0) {
      conditions.value = rawConditions.map(item => normalizeCondition(item))
      return
    }
  } catch (error) {
    console.error('loadSavedSelector error:', error)
  }

  conditions.value = [defaultCondition()]
}

const saveForm = async () => {
  const payload = {
    strategyName,
    conditions: conditions.value,
  }

  try {
    const response = await axios.post('/api/strategy/getStockSelector/', payload, { withCredentials: true })
    emit('update:selector', response.data)
    ElMessage.success('策略已保存')
  } catch (error) {
    console.error('saveForm error:', error)
    ElMessage.error(error.response?.data?.error || '保存策略失败，请重试')
  }
}

onMounted(async () => {
  await fetchUploadedStrategies()
  await loadSavedSelector()
})
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

.upload-panel,
.uploaded-panel {
  margin-bottom: 20px;
  padding: 18px 20px;
  border: 1px solid #dbe4f0;
  border-radius: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f7fc 100%);
}

.upload-panel {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
}

.upload-copy h3,
.uploaded-header h3 {
  margin: 0 0 10px;
  font-size: 16px;
}

.upload-copy p {
  margin: 0 0 8px;
  color: #425466;
  line-height: 1.6;
}

.upload-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.hidden-input {
  display: none;
}

.uploaded-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.uploaded-count {
  font-size: 12px;
  color: #5b7083;
}

.uploaded-list {
  display: grid;
  gap: 12px;
}

.uploaded-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e4ebf3;
}

.uploaded-name {
  font-weight: bold;
  color: #15314b;
}

.uploaded-meta,
.uploaded-empty,
.extra-cell {
  color: #5b7083;
  font-size: 13px;
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
.btn-delete,
.btn-upload,
.btn-refresh,
.btn-add-custom,
.btn-template {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
  font-weight: bold;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary,
.btn-upload {
  background-color: #4caf50;
}

.btn-save,
.btn-refresh,
.btn-add-custom,
.btn-confirm {
  background-color: #2196f3;
}

.btn-template {
  background-color: #0f766e;
}

.btn-delete {
  background-color: #f44336;
}

.btn-primary:disabled,
.btn-save:disabled,
.btn-delete:disabled,
.btn-upload:disabled,
.btn-refresh:disabled,
.btn-add-custom:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

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
  color: white;
}

@media (max-width: 960px) {
  .upload-panel,
  .uploaded-item {
    flex-direction: column;
    align-items: stretch;
  }

  .upload-actions,
  .button-group {
    flex-direction: column;
  }
}
</style>
