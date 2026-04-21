<template>
  <div class="page-wrapper">
    <!-- 顶部横向导航栏 -->
    <header class="c-header">
      <div class="c-header-wrapper-horizontal">
        <div class="header-logo">策略回测系统</div>
        <ul class="c-header-nav-ul-horizontal">
          <li>
            <RouterLink class="nav-link nav-link-home" to="/">首页</RouterLink>
          </li>
          <li><a :class="['nav-link', current === 'strategy' ? 'active' : '']" @click="current = 'strategy'">策略参数</a></li>
          <li><a :class="['nav-link', current === 'selector' ? 'active' : '']" @click="current = 'selector'">策略选择</a></li>
          <li><a :class="['nav-link', current === 'factor' ? 'active' : '']" @click="current = 'factor'">因子配置</a></li>
          <li><a :class="['nav-link', current === 'result' ? 'active' : '']" @click="current = 'result'">回测结果</a></li>
        </ul>
      </div>
    </header>

    <!-- 页面主内容区域 -->
    <main class="main-container">
      <section v-if="current === 'strategy'" class="main-box strategy-box">
        <StrategyConfig @update:strategy="handleStrategy" />
      </section>

      <section v-else-if="current === 'factor'" class="main-box factor-box">
        <FactorConfig @update:factor="handleFactor" />
      </section>

      <section v-else-if="current === 'selector'" class="main-box selector-box">
        <StockSelector @update:selector="handleSelector" />
      </section>

      <section v-else-if="current === 'result'" class="main-box result-box">
        <BacktestTrigger :params="backtestParams">
          <template #summary="{ params }"><BacktestResult :params="params" /></template>
          <template #returns ="{ params }"><BacktestResult :params="params" /></template>
          <template #drawdown ="{ params }"><BacktestResult :params="params" /></template>
        </BacktestTrigger>
      </section>

      <TradeDrawer :visible="drawerVisible" :detail="drawerData" @close="drawerVisible = false" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import StrategyConfig from '@/components/strategy_new/StrategyConfig.vue'
import FactorConfig from '@/components/strategy_new/FactorConfig.vue'
import StockSelector from '@/components/strategy_new/StockSelector.vue'
import BacktestTrigger from '@/components/strategy_new/BacktestTriggerFixed.vue'
import BacktestResult from '@/components/strategy_new/BacktestResult.vue'
import TradeDrawer from '@/components/strategy_new/TradeDrawer.vue'

const route = useRoute()
const strategyId = ref('')

onMounted(() => {
  strategyId.value = route.params.id
  // 根据 strategyId 获取策略详情并展示
})

const current = ref('strategy')
const drawerVisible = ref(false)
const drawerData = ref({})
const backtestParams = ref({
  strategy: {}, // 来自 StrategyConfig.vue
  factor: {},   // 来自 FactorConfig.vue
  selector: {}  // 来自 StockSelector.vue
})

const handleStrategy = (data) => {
  console.log('收到策略数据:', data)
  backtestParams.value.strategy = data
}

const handleFactor = (data) => {
  console.log('收到因子数据:', data)
  backtestParams.value.factor = data
}

const handleSelector = (data) => {
  console.log('收到选股器数据:', data)
  backtestParams.value.selector = data
}
</script>
<style scoped>
.page-wrapper {
  width: 100%;
  /* min-height: 100vh; */
  background: #f5f7fa;
  /* display: flex; */
  /* flex-direction: column; */
}



.c-header {
  width: 100%;
  background: #001f4a;
  color: white;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 999;
}

.c-header-wrapper-horizontal {
  display: flex;
  align-items: center;
  gap: 40px;
  height: 60px;
  padding: 0 30px;
}

.header-logo {
  font-size: 18px;
  font-weight: bold;
  color: white;
  white-space: nowrap;
}

.c-header-nav-ul-horizontal {
  display: flex;
  gap: 20px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-link {
  color: white;
  text-decoration: none;
  font-size: 14px;
  padding: 6px 16px;
  border-radius: 12px;
  transition: background 0.3s, color 0.3s;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
}

.nav-link.active {
  background: white;
  color: #00204a;
  font-weight: bold;
}

.main-container {
  /* padding: 24px 40px; */
  width: 100%;
 display: flex;
  justify-content: flex-start; /* 水平靠左 */
  align-items: flex-start; /* 垂直靠上 */
}

/* main-box: 不居中、不限宽 */
.main-box {
  width: 100%;
  margin: 0;
  /* padding: 40px; */
  box-sizing: border-box;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.strategy-box form > div {
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
}

.strategy-box label {
  margin-bottom: 6px;
  font-weight: 500;
  color: #333;
}

.strategy-box input,
.strategy-box select {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 8px;
  font-size: 14px;
  width: 300px;
  max-width: 100%;
}

.strategy-box button {
  margin-top: 20px;
  width: 160px;
  padding: 10px 0;
  background: #0055cc;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.strategy-box button:hover {
  background: #003f99;
}
</style>
