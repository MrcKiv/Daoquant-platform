<template>
  <div class="indicator-container">
    <div 
      v-for="(item, index) in indicatorList" 
      :key="index"
      class="indicator-item"
      :class="indicatorClass(item.value)"
    >
      <div class="indicator-label">{{ item.label }}</div>
      <div class="indicator-value">
        {{ formatValue(item.value) }}
        <span class="indicator-unit">{{ item.unit }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  macd: Number,
  kdj: Number,
  wr: Number,
  boll: Number,
  cci: Number
})

const indicatorList = computed(() => [
  { label: 'MACD', value: props.macd, unit: '点' },
  { label: 'KDJ', value: props.kdj, unit: '%' },
  { label: '威廉指标', value: props.wr, unit: '%' },
  { label: '布林线', value: props.boll, unit: '点' },
  { label: 'CCI', value: props.cci, unit: '点' }
])

const formatValue = (value) => {
  return value !== null ? value.toFixed(2) : '--'
}

const indicatorClass = (value) => {
  if (value === null) return 'neutral'
  return value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral'
}
</script>

<style scoped>
.indicator-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin: 24px 0;
}

.indicator-item {
  background: white;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  text-align: center;
}

.indicator-label {
  font-size: 0.95rem;
  color: #666;
  margin-bottom: 8px;
}

.indicator-value {
  font-size: 1.4rem;
  font-weight: 600;
}

.indicator-unit {
  font-size: 0.9rem;
  color: #999;
  margin-left: 4px;
}

.positive { color: #27ae60; }
.negative { color: #e74c3c; }
.neutral { color: #3498db; }
</style>