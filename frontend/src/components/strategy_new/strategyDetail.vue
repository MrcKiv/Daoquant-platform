<!-- src/components/strategy_new/BacktestReport.vue -->
<!-- src/components/strategy_new/BacktestReport.vue (模板部分) -->
<template>
  <div id="pdf-report-container" class="pdf-report-container">
    <!-- 页眉 -->
    <div class="header running-header">
      <div class="header-content">
        <span>内部自用</span>
        <span class="page-number"></span>
      </div>
    </div>

    <!-- 封面页 -->
    <div class="cover-page">
      <!-- Logo 和标题 -->
      <div class="header" style="text-align: center; margin-bottom: 30px;">
        <div style="display: flex; justify-content: flex-end; margin-bottom: 20px;">
          <div class="logo-placeholder">Logo</div>
        </div>
        <h1 style="font-size: 28px; font-weight: bold; color: #000; margin: 60px 0 30px;">内部自用</h1>
        <h2 style="font-size: 24px; font-weight: bold; color: #000; margin: 20px 0;">策略回测报告</h2>
        <div class="report-info">
          <p><strong>策略名称：</strong>{{ strategyName || '未命名策略' }}</p>
          <p><strong>生成日期：</strong>{{ currentDate }}</p>
        </div>
      </div>
    </div>

    <div class="page-break"></div>

    <!-- 目录页 -->
    <div class="toc-page">
      <div class="toc-header">
        <h3 style="font-size: 20px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px; margin-bottom: 20px;">目录</h3>
      </div>
      <div class="toc-content">
        <ol style="padding-left: 20px; margin: 15px 0;">
          <li style="margin: 12px 0; font-size: 16px;"><a href="#section1">一、策略说明</a></li>
          <li style="margin: 12px 0; font-size: 16px;"><a href="#section2">二、回测设置</a></li>
          <li style="margin: 12px 0; font-size: 16px;"><a href="#section3">三、回测结果</a></li>
        </ol>
      </div>
    </div>

    <div class="page-break"></div>

    <!-- 一、策略说明 -->
    <div id="section1" class="section">
      <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px; margin-top: 0;">一、策略说明</h3>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">策略买卖逻辑</h4>
      <p style="margin: 10px 0; line-height: 1.6;">
        {{ strategyConfig.description || '未提供策略详细说明' }}
      </p>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">策略特征标签</h4>
      <p style="margin: 10px 0; line-height: 1.6;">
        {{ getStrategyTags() }}
      </p>
    </div>

    <div class="page-break"></div>

    <!-- 二、回测设置 -->
    <div id="section2" class="section">
      <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px;">二、回测设置</h3>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">回测指标和值</h4>
      <div class="summary-table" style="margin: 15px 0;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">
          <thead>
            <tr style="background-color: #f2f2f2;">
              <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">指标</th>
              <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">值</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, i) in summary" :key="i">
              <td style="padding: 8px; border: 1px solid #ddd;">{{ item.label }}</td>
              <td style="padding: 8px; border: 1px solid #ddd;">{{ item.value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="page-break"></div>

    <!-- 三、回测结果 -->
    <div id="section3" class="section">
      <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px;">三、回测结果</h3>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">回测股票统计</h4>
      <p style="margin: 10px 0; line-height: 1.6;">
        股票池共计{{ getStockCount() }}只股票（股票列表见附录）
      </p>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">回测结果图</h4>
      <div id="pdf-chart-container" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">回测特征反馈</h4>
      <div class="metrics-table" style="margin: 15px 0;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">
          <thead>
            <tr style="background-color: #f2f2f2;">
              <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">指标</th>
              <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">值</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="padding: 8px; border: 1px solid #ddd;">最大回撤</td>
              <td style="padding: 8px; border: 1px solid #ddd;">{{ formatPercentage(metrics?.strategy?.maxDrawdown || 0) }}%</td>
            </tr>
            <tr>
              <td style="padding: 8px; border: 1px solid #ddd;">年化收益</td>
              <td style="padding: 8px; border: 1px solid #ddd;">{{ formatPercentage(metrics?.strategy?.annualizedReturn || 0) }}%</td>
            </tr>
            <tr>
              <td style="padding: 8px; border: 1px solid #ddd;">夏普率</td>
              <td style="padding: 8px; border: 1px solid #ddd;">{{ (metrics?.strategy?.sharpeRatio || 0).toFixed(2) }}</td>
            </tr>
           <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">胜率</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{{ formatPercentage(metrics?.strategy?.winRate || 0) }}%</td>
          </tr>
          <!-- 新增索提诺比率指标 -->
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">索提诺比率</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{{ (metrics?.strategy?.sortinoRatio || 0).toFixed(2) }}</td>
          </tr>
          </tbody>
        </table>
      </div>


<!--      &lt;!&ndash; 新增：日收益表现图 &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">日收益表现图</h4>-->
<!--      <div id="daily-return-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：收益分析 &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">收益分析</h4>-->
<!--      <div id="period-returns-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：年度回报 &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">年度回报</h4>-->
<!--      <div id="annual-returns-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

      <!-- 新增：个股绩效归因（盈利前十） -->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">个股绩效归因（盈利前十）</h4>-->
<!--      <div id="stock-performance-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：个股绩效归因（亏损前十） &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">个股绩效归因（亏损前十）</h4>-->
<!--      <div id="stock-performance-loss-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：申万行业配置时序 &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">申万行业配置时序</h4>-->
<!--      <div id="industry-allocation-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：持股数量时序 &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">持股数量时序</h4>-->
<!--      <div id="holdings-timeline-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：持股行业分析 &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">持股行业分析</h4>-->
<!--      <div id="industry-holdings-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：期末市值占比 &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">期末市值占比</h4>-->
<!--      <div id="end-period-market-value-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：交易类型分析（买入） &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">交易类型分析（买入）</h4>-->
<!--      <div id="transaction-type-analysis-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->

<!--      &lt;!&ndash; 新增：交易类型分析（卖出） &ndash;&gt;-->
<!--      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">交易类型分析（卖出）</h4>-->
<!--      <div id="transaction-type-analysis-sell-chart" style="width: 100%; height: 400px; background: white; margin: 15px 0; border: 1px solid #ddd;"></div>-->



      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">买卖股分析</h4>
      <p style="margin: 10px 0; line-height: 1.6;">
        本策略在{{ formatDate(tradeStartDate) }} 至 {{ formatDate(tradeEndDate) }}回测期间共进行 {{ calculateStockProfitLoss.length }} 笔交易。<br>
        其中<span :style="{ color: profitableTradesCount > 0 ? 'red' : 'green' }">
          盈利交易 {{ profitableTradesCount }} 笔，盈利共计 {{ formatCurrency(totalProfit) }} 元。
        </span>
        <span style="color: green"><br>
          亏损交易 {{ lossTradesCount }} 笔，亏损共计 {{ formatCurrency(Math.abs(totalLoss)) }} 元。
        </span>

        <span :style="{ color: (totalProfit + totalLoss) >= 0 ? 'red' : 'green' }"><br>
          最终{{ (totalProfit + totalLoss) >= 0 ? '盈利' : '亏损' }} {{ formatCurrency(Math.abs(totalProfit + totalLoss)) }} 元
        </span>。
      </p>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">买卖股明细表</h4>
      <div class="trades-table" style="margin: 15px 0;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; font-size: 12px;">
          <thead>
            <tr style="background-color: #f2f2f2;">
              <th style="padding: 8px; border: 1px solid #ddd;">交易日期</th>
              <th style="padding: 8px; border: 1px solid #ddd;">股票代码</th>
              <th style="padding: 8px; border: 1px solid #ddd;">买卖标识</th>
              <th style="padding: 8px; border: 1px solid #ddd;">数量(手)</th>
              <th style="padding: 8px; border: 1px solid #ddd;">每股单价（元)</th>
              <th style="padding: 8px; border: 1px solid #ddd;">交易资金（元）</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(trade, index) in sampleTrades" :key="index">
              <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.date }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.code }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.side }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.quantity }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.price }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ trade.amount }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">股票盈亏统计表</h4>
      <div class="profit-table" style="margin: 15px 0;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; font-size: 12px;">
          <thead>
            <tr style="background-color: #f2f2f2;">
              <th style="padding: 8px; border: 1px solid #ddd;">持股开始日期</th>
              <th style="padding: 8px; border: 1px solid #ddd;">持股终止日期</th>
              <th style="padding: 8px; border: 1px solid #ddd;">股票代码</th>
              <th style="padding: 8px; border: 1px solid #ddd;">买入价格</th>
              <th style="padding: 8px; border: 1px solid #ddd;">卖出价格</th>
              <th style="padding: 8px; border: 1px solid #ddd;">成交手数</th>
              <th style="padding: 8px; border: 1px solid #ddd;">盈亏资金</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(profit, index) in calculateStockProfitLoss" :key="index">
              <td style="padding: 6px; border: 1px solid #ddd;">{{ formatDate(profit['持股开始日期']) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ formatDate(profit['持股终止日期']) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['股票代码'] }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['买入价格'].toFixed(2) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['卖出价格'].toFixed(2) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['成交手数'] }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;" :style="{ color: profit['盈亏资金'] >= 0 ? 'red' : 'green' }">
                {{ profit['盈亏资金'].toFixed(2) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <h4 style="font-size: 16px; font-weight: bold; margin: 15px 0 10px;">盈利股票</h4>
      <div class="winning-stocks" style="margin: 15px 0;">
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd; font-size: 12px;">
          <thead>
            <tr style="background-color: #f2f2f2;">
              <th style="padding: 8px; border: 1px solid #ddd;">持股开始日期</th>
              <th style="padding: 8px; border: 1px solid #ddd;">持股终止日期</th>
              <th style="padding: 8px; border: 1px solid #ddd;">股票代码</th>
              <th style="padding: 8px; border: 1px solid #ddd;">买入价格</th>
              <th style="padding: 8px; border: 1px solid #ddd;">卖出价格</th>
              <th style="padding: 8px; border: 1px solid #ddd;">成交手数</th>
              <th style="padding: 8px; border: 1px solid #ddd;">盈亏资金</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(profit, index) in profitableStocks" :key="index">
              <td style="padding: 6px; border: 1px solid #ddd;">{{ formatDate(profit['持股开始日期']) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ formatDate(profit['持股终止日期']) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['股票代码'] }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['买入价格'].toFixed(2) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['卖出价格'].toFixed(2) }}</td>
              <td style="padding: 6px; border: 1px solid #ddd;">{{ profit['成交手数'] }}</td>
              <td style="padding: 6px; border: 1px solid #ddd; color: red;">
                {{ profit['盈亏资金'].toFixed(2) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="page-break"></div>

    <!-- 附录 -->
    <div class="appendix">
      <h3 style="font-size: 18px; font-weight: bold; border-bottom: 2px solid #333; padding-bottom: 5px;">附录：股票列表</h3>
      <p style="margin: 10px 0; line-height: 1.6;">
        {{ getStockList() }}
      </p>
    </div>
  </div>
</template>

<!-- src/components/strategy_new/BacktestReport.vue (script 部分) -->
<!-- src/components/strategy_new/BacktestReport.vue (脚本部分) -->
<script setup>
// ... 保持原有脚本代码不变 ...
import * as echarts from 'echarts'
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useGeneratePDF } from '@/stores/useGeneratePDF'

const route = useRoute()
const strategyName = route.query.strategyName
const showDownloadPrompt = route.query.downloadPrompt === 'true'

// 当前日期
const currentDate = new Date().toLocaleDateString('zh-CN')

// 数据存储
const strategyConfig = ref({})
const backtestResult = ref({})
const factorConfig = ref([])
const selectorConfig = ref([])
const metrics = ref({})
// 从后端获取的真实交易数据
const realTrades = computed(() => {
  const trades = []
  if (backtestResult.value.trades) {
    // 遍历交易数据，按日期组织
    for (const [date, tradeList] of Object.entries(backtestResult.value.trades)) {
      tradeList.forEach(trade => {
        trades.push({
          date: date,
          code: trade.st_code || '',
          // name: trade.st_name || '-', // 如果后端提供股票名称
          side: trade.trade_type || '',
          quantity: trade.number_of_transactions || 0,
          price: trade.trade_price || 0,
          amount: trade.turnover || (trade.trade_price * trade.number_of_transactions) || 0
        })
      })
    }
  }
  return trades
})

// 示例数据（实际应用中应从后端获取）
const sampleTrades = computed(() => {
  return realTrades.value.length > 0 ? realTrades.value : [
    { date: '2024-01-15', code: '000001', name: '平安银行', side: '买入', quantity: 100, price: 12.5, amount: 125000 },
    { date: '2024-02-20', code: '000002', name: '万科A', side: '卖出', quantity: 50, price: 25.8, amount: 129000 }
  ]
})
// const profitableTrades = ref(15)
// const lossTrades = ref(8)
const profitableTradesCount = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss.filter(item => item['盈亏资金'] > 0).length;
  }
  return 0;
});

const lossTradesCount = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss.filter(item => item['盈亏资金'] < 0).length;
  }
  return 0;
});

const totalProfit = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss
      .filter(item => item['盈亏资金'] > 0)
      .reduce((sum, item) => sum + item['盈亏资金'], 0);
  }
  return 0;
});

const totalLoss = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss
      .filter(item => item['盈亏资金'] < 0)
      .reduce((sum, item) => sum + item['盈亏资金'], 0);
  }
  return 0;
});

// 添加货币格式化函数
const formatCurrency = (value) => {
  return value.toFixed(2);
};

const tradeStartDate = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss && backtestResult.value.calculate_stock_profit_loss.length > 0) {
    // 获取最早的持股开始日期
    const dates = backtestResult.value.calculate_stock_profit_loss.map(item => item['持股开始日期']);
    return Math.min(...dates.map(date => parseInt(date)));
  }
  return null;
});

const tradeEndDate = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss && backtestResult.value.calculate_stock_profit_loss.length > 0) {
    // 获取最晚的持股终止日期
    const dates = backtestResult.value.calculate_stock_profit_loss.map(item => item['持股终止日期']);
    return Math.max(...dates.map(date => parseInt(date)));
  }
  return null;
});
const calculateStockProfitLoss = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    return backtestResult.value.calculate_stock_profit_loss
  }
  return []
})

// 添加日期格式化函数
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  // 将 YYYYMMDD 格式转换为 YYYY-MM-DD
  const dateStrFormatted = dateStr.toString()
  if (dateStrFormatted.length === 8) {
    const year = dateStrFormatted.substring(0, 4)
    const month = dateStrFormatted.substring(4, 6)
    const day = dateStrFormatted.substring(6, 8)
    return `${year}-${month}-${day}`
  }
  return dateStr
}

// const sampleProfits = ref([
//   { startDate: '2024-01-15', endDate: '2024-02-20', code: '000001', name: '平安银行', profit: '+15000' }
// ])
// const winningStocks = ref([
//   { code: '000001', name: '平安银行', industry: '银行', concepts: ['金融', '蓝筹'] }
// ])
const profitableStocks = computed(() => {
  if (backtestResult.value.calculate_stock_profit_loss) {
    // 筛选出盈亏资金为正数的股票（盈利股票）
    return backtestResult.value.calculate_stock_profit_loss.filter(item => item['盈亏资金'] > 0);
  }
  return [];
});

// 表格数据
const summary = computed(() => {
  const s = strategyConfig.value || {}
  const f = factorConfig.value || []
  const sel = selectorConfig.value?.[0] || {}

  const factorStr = f.map(item => `${item.name || item.factor || ''}${item.operator || ''}${item.value || ''}`).join('、')

  return [
    { label: '初始资金', value: `${s.capital || s.init_fund}万元` },
    { label: '持股比例', value: `${s.ratio || 100}%` },
    { label: '持股数目', value: `${s.hold || s.max_hold_num}只` },
    { label: '收益基准', value: s.benchmark || s.income_base || '-' },
    { label: '时间范围', value: `${s.start_date} 至 ${s.end_date}` },
    { label: '选股范围', value: `板块(${s.scope || '全部'})、风格(${s.scope || '全部'})、行业(${s.scope || '全部'})` },
    { label: '因子', value: factorStr || '-' },
    { label: '因子合成', value: sel.operator || '-' }
  ]
})

// 图表数据
const trade_date = computed(() => backtestResult.value.dates || [])
const income_base_price = computed(() => {
  if (backtestResult.value.benchmarkReturns) {
    return backtestResult.value.benchmarkReturns.map(r => r * 100)
  }
  return []
})
const backData = computed(() => {
  if (backtestResult.value.strategyReturns) {
    return backtestResult.value.strategyReturns.map(r => r * 100)
  }
  return []
})
const ShareHolding_stock = computed(() => backtestResult.value.ShareHolding_stock || {})
const TradeData = computed(() => backtestResult.value.trades || {})

// 计算方法
const getStrategyTags = () => {
  const s = strategyConfig.value || {}
  const metricsData = metrics.value?.strategy || {}

  // 根据策略参数生成标签
  const tags = []
  if ((s.ratio || 100) > 50) tags.push('集中型')
  else tags.push('分散型')

  if (metricsData.annualizedReturn > 0.3) tags.push('高收益型')
  else if (metricsData.annualizedReturn > 0.1) tags.push('稳健型')
  else tags.push('保守型')

  if ((metricsData.maxDrawdown || 0) > -0.2) tags.push('低风险型')
  else tags.push('高风险型')

  return tags.join('、') || '未分类'
}

const getStockCount = () => {
  // 从持仓数据中计算股票数量
  const holdings = ShareHolding_stock.value
  if (Object.keys(holdings).length > 0) {
    const allStocks = new Set()
    Object.values(holdings).forEach(stocks => {
      stocks.forEach(stock => allStocks.add(stock))
    })
    return allStocks.size
  }
  return 0
}

const getStockList = () => {
  // 从持仓数据中获取股票列表
  const holdings = ShareHolding_stock.value
  if (Object.keys(holdings).length > 0) {
    const allStocks = new Set()
    Object.values(holdings).forEach(stocks => {
      stocks.forEach(stock => allStocks.add(stock))
    })
    return Array.from(allStocks).join(', ')
  }
  return '暂无股票数据'
}

const formatPercentage = (value) => {
  return (value * 100).toFixed(2)
}

// 加载策略配置
const loadStrategyConfig = async () => {
  try {

    const res = await axios.post('/api/strategy/loadStrategyConfig/', {
      strategyName: strategyName
    }, {
      withCredentials: true
    })

    if (res.data.success) {
      // 更新策略配置数据
      strategyConfig.value = res.data.backtest_config || res.data.received_data || {}

      // 解析并存储因子和选股器配置
      try {
        if (res.data.backtest_config?.bottomfactor) {
          factorConfig.value = JSON.parse(res.data.backtest_config.bottomfactor.replace(/'/g, '"'))
        }
        if (res.data.backtest_config?.optionfactor) {
          selectorConfig.value = JSON.parse(res.data.backtest_config.optionfactor.replace(/'/g, '"'))
        }
      } catch (e) {
        console.error('解析因子或选股器配置失败:', e)
      }

      // 存储backtest_result数据用于图表显示
      if (res.data.backtest_result && Object.keys(res.data.backtest_result).length > 0) {
        backtestResult.value = res.data.backtest_result
        metrics.value = res.data.backtest_result.metrics || {}
      }

      console.log('加载策略配置成功:', res.data)
    } else {
      console.error('加载策略失败:', res.data.message)
      alert('加载策略失败: ' + res.data.message)
    }
  } catch (err) {
    console.error('请求失败:', err)
    alert('加载策略失败，请检查网络或稍后重试')
  }
}

// 初始化图表
const initChart = () => {
  const container = document.getElementById('pdf-chart-container')
  if (!container) return

  const chart = echarts.init(container)

  const option = {
    title: {
      text: '回测数据图',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: function (params) {
        let date = params[0].name
        let year = date.slice(0, 4)
        let month = date.slice(4, 6)
        let day = date.slice(6, 8)
        let content = `${year}-${month}-${day}<br/>`

        for (let i = 0; i < params.length; i++) {
          content += `${params[i].seriesName} : ${params[i].value}%<br/>`
        }

        if (ShareHolding_stock.value && ShareHolding_stock.value[date]) {
          const stocks = ShareHolding_stock.value[date]
          content += `当日持仓: ${stocks.join(', ')}`
        } else {
          content += '当日持仓: 空仓'
        }

        return content
      }
    },
    legend: {
      data: ['沪深300收益率', '策略收益率']
    },
    grid: {
      left: '8%',
      right: '4%',
      bottom: '15%',
      containLabel: true,
      backgroundColor: 'transparent'
    },
    xAxis: {
      type: 'category',
      data: trade_date.value,
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}%',
        fontSize: 10
      }
    },
    series: [
      {
        name: '沪深300收益率',
        type: 'line',
        data: income_base_price.value,
        lineStyle: { color: 'red' },
        itemStyle: { color: 'red' },
        smooth: true
      },
      {
        name: '策略收益率',
        type: 'line',
        data: backData.value,
        lineStyle: { color: 'blue' },
        itemStyle: { color: 'blue' },
        smooth: true
      }
    ]
  }

  chart.setOption(option)
}

const initDailyReturnChart = () => {
  const chartDom = document.getElementById('daily-return-chart')
  const myChart = echarts.init(chartDom)

  // 从 backtestResult.value.daily_returns 获取数据
  const dailyReturnsData = backtestResult.value.daily_returns || []

  // 转换数据格式
  const categories = dailyReturnsData.map(item => item['日期'])
  const strategyReturns = dailyReturnsData.map(item => (item['日收益率'] * 100).toFixed(2))
  const benchmarkReturns = dailyReturnsData.map(item => (item['日收益率（基准）'] * 100).toFixed(2))

  const option = {
    title: {
      text: '日收益',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },

    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: params => {
        const date = params[0].axisValue
        const strategy = params[0].value + '%'
        const benchmark = params[1].value + '%'
        return `${date}<br/>
                <span style="color: #91cc75;">日收益率: ${strategy}</span><br/>
                <span style="color: #5470c6;">日收益率（基准）: ${benchmark}</span>`
      }
    },
    legend: {
      data: ['日收益率', '日收益率（基准）'],
      bottom: 10,
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    grid: {
      left: '5%',
      right: '5%',
      bottom: '20%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: '#666'
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '收益率 (%)',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}%',
        color: '#666',
        fontSize: 10
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      },
      min: value => Math.floor(value.min / 2) * 2,  // 保证负值显示完整
      max: value => Math.ceil(value.max / 2) * 2
    },
    series: [
      {
        name: '日收益率',
        type: 'bar',
        data: strategyReturns,
        itemStyle: {
          color: '#91cc75',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#7bb55c'
          }
        },
        barGap: '0%'
      },
      {
        name: '日收益率（基准）',
        type: 'bar',
        data: benchmarkReturns,
        itemStyle: {
          color: '#5470c6',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#4a5bb8'
          }
        }
      }
    ]
  }

  myChart.setOption(option)
  window.addEventListener('resize', myChart.resize)
}

const initPeriodReturnChart = () => {
  const chartDom = document.getElementById('period-returns-chart');
  const myChart = echarts.init(chartDom);

  const periodReturnsData = backtestResult.value.period_returns || [];

  // 从后端数据中提取周期名称
  const categories = periodReturnsData.map(item => item.period);

  // 正确映射后端返回的字段名
  const strategyReturns = periodReturnsData.map(item =>
    item.strategy_return !== null ? (item.strategy_return * 100).toFixed(2) : null
  );

  const benchmarkReturns = periodReturnsData.map(item =>
    item.benchmark_return !== null ? (item.benchmark_return * 100).toFixed(2) : null
  );

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        let result = params[0].name + '<br/>';
        params.forEach(param => {
          if (param.data !== null) {
            result += `${param.marker}${param.seriesName}：${param.data}%<br/>`;
          }
        });
        return result;
      }
    },
    legend: {
      bottom: 0,
      data: ['策略收益率', '基准收益率']
    },
    grid: {
      top: '10%',
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisTick: { alignWithLabel: true },
      axisLabel: {
        color: '#666',
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}%',
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          type: 'dashed',
          color: '#eee'
        }
      }
    },
    series: [
      {
        name: '策略收益率',
        type: 'bar',
        barWidth: '30%',
        data: strategyReturns,
        itemStyle: {
          color: '#ff0000'
        },
        emphasis: {
          focus: 'series'
        }
      },
      {
        name: '基准收益率',
        type: 'bar',
        barWidth: '30%',
        data: benchmarkReturns,
        itemStyle: {
          color: '#0000ff'
        },
        emphasis: {
          focus: 'series'
        }
      }
    ]
  };

  myChart.setOption(option);

  // 添加窗口大小调整事件监听器
  window.addEventListener('resize', myChart.resize);
};

const initAnnualReturnChart = () => {
  const chartDom = document.getElementById('annual-returns-chart');
  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.annual_returns 获取数据
  // 后端返回的是数组格式
  const annualDataArray = backtestResult.value.annual_returns || [];

  // 提取数据（假设数组中只有一个元素）
  const annualData = annualDataArray.length > 0 ? annualDataArray[0] : {};
  const productReturn = annualData.strategy_return !== undefined ? annualData.strategy_return : 0;
  const benchmarkReturn = annualData.benchmark_return !== undefined ? annualData.benchmark_return : 0;

  const option = {
    title: {
      text: '年度回报',
      left: '0',
      top: '0',
      textStyle: {
        fontSize: 12,
        fontWeight: 'normal'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        return params
          .map(p => `${p.seriesName}：${(p.value * 100).toFixed(2)}%`)
          .join('<br/>');
      }
    },
    legend: {
      bottom: 0,
      data: ['产品', '基准']
    },
    grid: {
      top: 50,
      left: 50,
      right: 20,
      bottom: 50
    },
    xAxis: {
      type: 'category',
      data: ['YTD'],
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: value => `${(value * 100).toFixed(0)}%`
      },
      splitLine: {
        lineStyle: { type: 'solid', color: '#eee' }
      }
    },
    series: [
      {
        name: '产品',
        type: 'bar',
        data: [productReturn],
        itemStyle: {
          color: '#ff0000' // 粉红色
        },
        barWidth: '20%'
      },
      {
        name: '基准',
        type: 'bar',
        data: [benchmarkReturn],
        itemStyle: {
          color: '#0000ff' // 浅蓝灰色
        },
        barWidth: '20%'
      }
    ]
  };

  myChart.setOption(option);
};

const initStockPerformanceChart = () => {
  // console.log('初始化个股绩效归因图表');
  // console.log('backtestResult.value:', backtestResult.value);
  // console.log('stock_performance_attribution_range:', backtestResult.value.stock_performance_attribution_range);

  const chartDom = document.getElementById('stock-performance-chart');
  if (!chartDom) {
    // console.error('找不到图表容器: stock-performance-chart');
    return;
  }

  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.stock_performance_attribution_range 获取数据
  let stockPerformanceData = backtestResult.value.stock_performance_attribution_range || [];
  // console.log('个股绩效归因数据:', stockPerformanceData);

  // 如果没有数据，尝试使用全部数据
  if (stockPerformanceData.length === 0) {
    const allStockData = backtestResult.value.stock_performance_attribution || [];
    // console.log('尝试使用全部个股绩效归因数据:', allStockData);
    if (allStockData.length > 0) {
      stockPerformanceData = allStockData;
    }
  }

  if (stockPerformanceData.length === 0) {
    // 如果没有数据，显示空状态
    // console.log('个股绩效归因数据为空，显示空状态');
    myChart.setOption({
      title: {
        text: '暂无个股绩效归因数据',
        subtext: '可能原因：\n1. 当前策略没有持仓股票\n2. 所有股票都处于亏损状态\n3. 数据尚未加载完成\n4. 数据格式问题',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  // 提取数据
  const stockNames = stockPerformanceData.map(item => item.stock_name);
  const weights = stockPerformanceData.map(item => item.weight_percentage);
  const profits = stockPerformanceData.map(item => item.profit_amount_wan);

  const option = {
    title: {
      text: '个股绩效归因（盈利前十）',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: '#999'
        }
      },
      formatter: function (params) {
        const stockName = params[0].name;
        const weight = params[0].value;
        const profit = params[1].value;
        return `${stockName}<br/>
                <span style="color: #91cc75;">平均权重: ${weight}%</span><br/>
                <span style="color: #5470c6;">收益额: ${profit}万元</span>`;
      }
    },
    legend: {
      data: ['平均权重', '收益额'],
      bottom: 10,
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    grid: {
      left: '8%',
      right: '4%',
      bottom: '20%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: stockNames,
      axisPointer: {
        type: 'shadow'
      },
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: '#666'
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '平均权重 (%)',
        min: 0,
        nameTextStyle: {
          color: '#666',
          fontSize: 12
        },
        axisLabel: {
          formatter: '{value}%',
          color: '#666',
          fontSize: 10
        },
        axisLine: {
          lineStyle: {
            color: '#ddd'
          }
        },
        axisTick: {
          lineStyle: {
            color: '#ddd'
          }
        },
        splitLine: {
          lineStyle: {
            color: '#f0f0f0',
            type: 'dashed'
          }
        }
      },
      {
        type: 'value',
        name: '收益额 (万元)',
        min: 0,
        nameTextStyle: {
          color: '#666',
          fontSize: 12
        },
        axisLabel: {
          formatter: '{value}',
          color: '#666',
          fontSize: 10
        },
        axisLine: {
          lineStyle: {
            color: '#ddd'
          }
        },
        axisTick: {
          lineStyle: {
            color: '#ddd'
          }
        },
        splitLine: {
          show: false
        }
      }
    ],
    series: [
      {
        name: '平均权重',
        type: 'bar',
        data: weights,
        itemStyle: {
          color: '#91cc75',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#7bb55c'
          }
        }
      },
      {
        name: '收益额',
        type: 'line',
        yAxisIndex: 1,
        data: profits,
        smooth: true,
        lineStyle: {
          color: '#5470c6',
          width: 3
        },
        itemStyle: {
          color: '#5470c6'
        },
        symbol: 'circle',
        symbolSize: 6
      }
    ]
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};

const initStockPerformanceLossChart = () => {
  const chartDom = document.getElementById('stock-performance-loss-chart');
  if (!chartDom) {
    return;
  }

  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.stock_performance_attribution_loss_range 获取数据
  const stockPerformanceLossData = backtestResult.value.stock_performance_attribution_loss_range || [];

  if (stockPerformanceLossData.length === 0) {
    // 如果没有数据，显示空状态
    myChart.setOption({
      title: {
        text: '暂无个股绩效归因（亏损前十）数据',
        subtext: '可能原因：\n1. 当前策略没有亏损股票\n2. 所有股票都处于盈利状态\n3. 数据尚未加载完成\n4. 数据格式问题',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  // 提取数据
  const stockNames = stockPerformanceLossData.map(item => item.stock_name);
  const weights = stockPerformanceLossData.map(item => item.weight_percentage);
  const losses = stockPerformanceLossData.map(item => item.loss_amount_wan);

  const option = {
    title: {
      text: '个股绩效归因（亏损前十）',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: '#999'
        }
      },
      formatter: function (params) {
        const stockName = params[0].name;
        const weight = params[0].value;
        const loss = params[1].value;
        return `${stockName}<br/>
                <span style="color: #fac858;">平均权重: ${weight}%</span><br/>
                <span style="color: #ee6666;">亏损额: ${loss}万元</span>`;
      }
    },
    legend: {
      data: ['平均权重', '亏损额'],
      bottom: 10,
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    grid: {
      left: '8%',
      right: '4%',
      bottom: '20%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: stockNames,
      axisPointer: {
        type: 'shadow'
      },
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: '#666'
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '平均权重 (%)',
        min: 0,
        nameTextStyle: {
          color: '#666',
          fontSize: 12
        },
        axisLabel: {
          formatter: '{value}%',
          color: '#666',
          fontSize: 10
        },
        axisLine: {
          lineStyle: {
            color: '#ddd'
          }
        },
        axisTick: {
          lineStyle: {
            color: '#ddd'
          }
        },
        splitLine: {
          lineStyle: {
            color: '#f0f0f0',
            type: 'dashed'
          }
        }
      },
      {
        type: 'value',
        name: '亏损额 (万元)',
        min: 0,
        nameTextStyle: {
          color: '#666',
          fontSize: 12
        },
        axisLabel: {
          formatter: '{value}',
          color: '#666',
          fontSize: 10
        },
        axisLine: {
          lineStyle: {
            color: '#ddd'
          }
        },
        axisTick: {
          lineStyle: {
            color: '#ddd'
          }
        },
        splitLine: {
          show: false
        }
      }
    ],
    series: [
      {
        name: '平均权重',
        type: 'bar',
        data: weights,
        itemStyle: {
          color: '#fac858',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#e6b800'
          }
        }
      },
      {
        name: '亏损额',
        type: 'line',
        yAxisIndex: 1,
        data: losses,
        smooth: true,
        lineStyle: {
          color: '#ee6666',
          width: 3
        },
        itemStyle: {
          color: '#ee6666'
        },
        symbol: 'circle',
        symbolSize: 6
      }
    ]
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};

const initIndustryAllocationChart = () => {
  const chartDom = document.getElementById('industry-allocation-chart');
  if (!chartDom) {
    return;
  }

  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.industry_allocation_timeline 获取数据
  const industryData = backtestResult.value.industry_allocation_timeline || {};

  if (!industryData.dates || !industryData.series || industryData.series.length === 0) {
    // 如果没有数据，显示空状态
    myChart.setOption({
      title: {
        text: '暂无申万行业配置时序数据',
        subtext: '可能原因：\n1. 当前策略没有持仓数据\n2. 行业数据未加载完成\n3. 数据格式问题',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  // 定义柔和的颜色方案
  const softColors = [
    '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272',
    '#fc8452', '#9a60b4', '#ea7ccc', '#5470c6', '#91cc75',
    '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452',
    '#9a60b4', '#ea7ccc', '#5470c6', '#91cc75', '#fac858',
    '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4'
  ];

  // 为每个系列添加样式配置
  const enhancedSeries = industryData.series.map((item, index) => ({
    ...item,
    smooth: true, // 添加平滑曲线
    lineStyle: {
      width: 0 // 隐藏线条，只显示面积
    },
    areaStyle: {
      opacity: 0.8, // 降低透明度
      color: softColors[index % softColors.length] // 使用柔和颜色
    },
    emphasis: {
      areaStyle: {
        opacity: 0.9 // 鼠标悬停时稍微提高透明度
      }
    }
  }));

  const option = {
    title: {
      text: '申万行业配置时序',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: function(params) {
        let result = params[0].axisValue + '<br/>';
        let total = 0;

        params.forEach(param => {
          if (param.data !== 0) {
            result += `${param.marker}${param.seriesName}: ${param.data.toFixed(2)}%<br/>`;
            total += param.data;
          }
        });

        result += `<br/><strong>总计: ${total.toFixed(2)}%</strong>`;
        return result;
      }
    },
    legend: {
      data: industryData.series.map(item => item.name),
      bottom: 10,
      type: 'scroll',
      textStyle: {
        fontSize: 11,
        color: '#666'
      },
      pageTextStyle: {
        color: '#666'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '20%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: industryData.dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: '#666',
        interval: 'auto'
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '占比 (%)',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}%',
        color: '#666',
        fontSize: 10
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      },
      min: 0,
      max: 100
    },
    series: enhancedSeries
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};

const initHoldingsTimelineChart = () => {
  const chartDom = document.getElementById('holdings-timeline-chart');
  if (!chartDom) {
    return;
  }

  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.holdings_timeline 获取数据
  const holdingsData = backtestResult.value.holdings_timeline || {};

  if (!holdingsData.dates || !holdingsData.total_holdings || !holdingsData.filtered_holdings) {
    // 如果没有数据，显示空状态
    myChart.setOption({
      title: {
        text: '暂无持股数量时序数据',
        subtext: '可能原因：\n1. 当前策略没有持仓数据\n2. 股票基本信息数据未加载完成\n3. 数据格式问题',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  const option = {
    title: {
      text: '持股数量时序',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: function(params) {
        const date = params[0].axisValue;
        let result = `${date}<br/>`;

        params.forEach(param => {
          if (param.data !== null && param.data !== undefined) {
            result += `${param.marker}${param.seriesName}: ${param.data}只<br/>`;
          }
        });

        return result;
      }
    },
    legend: {
      data: ['持股数量', '持股数量（删除新股）'],
      bottom: 10,
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '20%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: holdingsData.dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: '#666',
        interval: 'auto'
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '数量 (个数)',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        color: '#666',
        fontSize: 10
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      },
      min: 0
    },
    series: [
      {
        name: '持股数量',
        type: 'line',
        data: holdingsData.total_holdings,
        smooth: true,
        lineStyle: {
          color: '#ee6666',
          width: 3
        },
        itemStyle: {
          color: '#ee6666'
        },
        symbol: 'circle',
        symbolSize: 6
      },
      {
        name: '持股数量（删除新股）',
        type: 'line',
        data: holdingsData.filtered_holdings,
        smooth: true,
        lineStyle: {
          color: '#5470c6',
          width: 3
        },
        itemStyle: {
          color: '#5470c6'
        },
        symbol: 'circle',
        symbolSize: 6
      }
    ]
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};

const initIndustryHoldingsChart = () => {
  const chartDom = document.getElementById('industry-holdings-chart');
  if (!chartDom) {
    console.log('找不到图表容器: industry-holdings-chart');
    return;
  }

  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.industry_holdings_analysis 获取数据
  const industryData = backtestResult.value.industry_holdings_analysis || {};
  // console.log('持股行业分析数据:', industryData);

  if (!industryData.industries || !industryData.percentages || industryData.industries.length === 0) {
    // console.log('持股行业分析数据为空或格式不正确');
    // 如果没有数据，显示空状态
    myChart.setOption({
      title: {
        text: '暂无持股行业分析数据',
        subtext: '可能原因：\n1. 当前策略没有持仓数据\n2. 行业数据未加载完成\n3. 数据格式问题\n4. latest_value 字段为空',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  const option = {
    title: {
      text: '前十大行业市值占比 (%)',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const industry = params[0].name;
        const percentage = params[0].value;
        return `${industry}<br/>
                <span style="color: #ff0000;">市值占比: ${percentage}%</span>`;
      }
    },
    grid: {
      left: '4%',
      right: '10%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '占比 (%)',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}%',
        color: '#666',
        fontSize: 10
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      },
      min: 0,
      max: Math.ceil(Math.max(...industryData.percentages) / 2) * 2  // 向上取整到最近的2的倍数
    },
    yAxis: {
      type: 'category',
      data: industryData.industries,
      axisLabel: {
        color: '#666',
        fontSize: 11
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        show: false
      }
    },
    series: [
      {
        name: '市值占比',
        type: 'bar',
        data: industryData.percentages,
        itemStyle: {
          color: '#ff0000',
          borderRadius: [0, 2, 2, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#ff0000'
          }
        },
        barWidth: '60%'
      }
    ]
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};

const initEndPeriodMarketValueChart = () => {
  const chartDom = document.getElementById('end-period-market-value-chart');
  if (!chartDom) {
    return;
  }

  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.end_period_market_value_proportion 获取数据
  const marketValueData = backtestResult.value.end_period_market_value_proportion || {};

  if (!marketValueData.industries || !marketValueData.percentages || marketValueData.industries.length === 0) {
    // 如果没有数据，显示空状态
    myChart.setOption({
      title: {
        text: '暂无期末市值占比数据',
        subtext: '可能原因：\n1. 当前策略没有持仓数据\n2. 行业数据未加载完成\n3. 数据格式问题',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  // 定义颜色方案
  const colors = [
    '#ff0000', '#0000ff', '#91cc75', '#fac858', '#73c0de',
    '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#91cc75',
    '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452'
  ];

  const option = {
    title: {
      text: '期末市值占比',
      left: 'left',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        return `${params.name}<br/>
                <span style="color: ${params.color};">市值占比: ${params.value}%</span><br/>
                <span style="color: ${params.color};">市值: ${marketValueData.market_values[params.dataIndex]}万元</span>`;
      }
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      bottom: '10%',
      textStyle: {
        fontSize: 11,
        color: '#666'
      }
    },
    series: [
      {
        name: '市值占比',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '50%'],
        data: marketValueData.industries.map((industry, index) => ({
          name: industry,
          value: marketValueData.percentages[index]
        })),
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}%',
          fontSize: 10
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ],
    color: colors
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};

const initTransactionTypeAnalysisChart = () => {
  const chartDom = document.getElementById('transaction-type-analysis-chart');
  if (!chartDom) {
    return;
  }

  const myChart = echarts.init(chartDom);

  // 从 backtestResult.value.transaction_type_analysis 获取数据
  const transactionData = backtestResult.value.transaction_type_analysis || {};

  if (Object.keys(transactionData).length === 0) {
    // 如果没有数据，显示空状态
    myChart.setOption({
      title: {
        text: '暂无交易类型分析数据',
        subtext: '可能原因：\n1. 当前策略没有买入交易数据\n2. 大盘指数数据未加载完成\n3. 数据格式问题',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  // 提取数据
  const periods = Object.keys(transactionData);
  const trendPercentages = periods.map(period => transactionData[period].trend_percentage);
  const reversalPercentages = periods.map(period => transactionData[period].reversal_percentage);

  const option = {
    title: {
      text: '交易类型分析（买入）',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const period = params[0].axisValue;
        const trend = params[0].value;
        const reversal = params[1].value;
        return `${period}<br/>
                <span style="color: #ee6666;">趋势买入次数: ${trend}%</span><br/>
                <span style="color: #5470c6;">反转买入次数: ${reversal}%</span>`;
      }
    },
    legend: {
      data: ['趋势买入次数', '反转买入次数'],
      bottom: 10,
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '20%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: periods,
      axisLabel: {
        color: '#666',
        fontSize: 12
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '占比 (%)',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}%',
        color: '#666',
        fontSize: 10
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      },
      min: 0,
      max: 100
    },
    series: [
      {
        name: '趋势买入次数',
        type: 'bar',
        data: trendPercentages,
        itemStyle: {
          color: '#ff0000',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#ff0000'
          }
        },
        barGap: '0%'
      },
      {
        name: '反转买入次数',
        type: 'bar',
        data: reversalPercentages,
        itemStyle: {
          color: '#0000ff',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#0000ff'
          }
        }
      }
    ]
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};

const initTransactionTypeAnalysisSellChart = () => {
  const chartDom = document.getElementById('transaction-type-analysis-sell-chart');
  if (!chartDom) {
    return;
  }

  const myChart = echarts.init(chartDom);

  const transactionData = backtestResult.value.transaction_type_analysis_sell || {};

  if (Object.keys(transactionData).length === 0) {
    myChart.setOption({
      title: {
        text: '暂无交易类型分析（卖出）数据',
        subtext: '可能原因：\n1. 当前策略没有卖出交易数据\n2. 大盘指数数据未加载完成\n3. 数据格式问题',
        left: 'center',
        top: 'center',
        textStyle: {
          fontSize: 16,
          color: '#999'
        },
        subtextStyle: {
          fontSize: 12,
          color: '#ccc',
          lineHeight: 20
        }
      }
    });
    return;
  }

  const periods = Object.keys(transactionData);
  const trendPercentages = periods.map(period => transactionData[period].trend_percentage);
  const reversalPercentages = periods.map(period => transactionData[period].reversal_percentage);

  const option = {
    title: {
      text: '交易类型分析（卖出）',
      left: 'center',
      top: '10',
      textStyle: {
        fontSize: 18,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const period = params[0].axisValue;
        const trend = params[0].value;
        const reversal = params[1].value;
        return `${period}<br/>
                <span style="color: #ee6666;">趋势卖出次数: ${trend}%</span><br/>
                <span style="color: #0000ff;">反转卖出次数: ${reversal}%</span>`;
      }
    },
    legend: {
      data: ['趋势卖出次数', '反转卖出次数'],
      bottom: 10,
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '20%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: periods,
      axisLabel: {
        color: '#666',
        fontSize: 12
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '占比 (%)',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}%',
        color: '#666',
        fontSize: 10
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      },
      min: 0,
      max: 100
    },
    series: [
      {
        name: '趋势卖出次数',
        type: 'bar',
        data: trendPercentages,
        itemStyle: {
          color: '#ff0000',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#ff0000'
          }
        },
        barGap: '0%'
      },
      {
        name: '反转卖出次数',
        type: 'bar',
        data: reversalPercentages,
        itemStyle: {
          color: '#0000ff',
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: '#0000ff'
          }
        }
      }
    ]
  };

  myChart.setOption(option);
  window.addEventListener('resize', myChart.resize);
};
// 初始化 useGeneratePDF
const {
  generatePDF,
  isGenerating
} = useGeneratePDF({
  containerId: 'pdf-report-container',
  filename: '策略回测报告',
  format: 'a4',
  orientation: 'portrait',
  margin: [10, 5, 10, 5],
  scale: 2,
})

// 显示下载确认弹窗
const showDownloadConfirmation = () => {
  if (showDownloadPrompt) {
    setTimeout(() => {
      if (confirm('报告已生成完成，是否立即下载PDF文件？')) {
        generatePDF()
      }
    }, 1000) // 延迟1秒显示，确保页面渲染完成
  }
}

onMounted(async () => {
  // 加载策略配置和回测结果
  await loadStrategyConfig()

  // 初始化图表
  initChart()
  // initDailyReturnChart()
  // initStockPerformanceChart()
  //  initStockPerformanceLossChart()
  //  // 等待第一批图表渲染完成
  // await new Promise(resolve => setTimeout(resolve, 800))
  //  initPeriodReturnChart()
  // // initAnnualReturnChart()
  // // initIndustryAllocationChart()
  // //  initHoldingsTimelineChart()
  // //  initIndustryHoldingsChart()
  // // 等待第二批图表渲染完成
  // await new Promise(resolve => setTimeout(resolve, 800))
  // initEndPeriodMarketValueChart()
  //  initTransactionTypeAnalysisChart()
  //  initTransactionTypeAnalysisSellChart()

  // 延迟确保图表渲染完成
  await new Promise(resolve => setTimeout(resolve, 500))

  // // 显示下载确认弹窗
  showDownloadConfirmation()
})
</script>

<style scoped>
/* 页面容器样式 */
.pdf-report-container {
  width: 800px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  background: white;
  color: black;
  position: relative;
}

/* 页眉样式 */
.running-header {
  position: running(header);
  width: 100%;
  border-bottom: 1px solid #ccc;
  padding: 10px 0;
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #666;
}

/* 封面页样式 */
.cover-page {
  text-align: center;
  padding: 40px 0;
}

.logo-placeholder {
  width: 100px;
  height: 100px;
  border: 1px dashed #999;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #999;
}

.report-info {
  margin-top: 80px;
  text-align: left;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.report-info p {
  margin: 10px 0;
  font-size: 16px;
}

/* 目录页样式 */
.toc-page {
  padding: 20px 0;
}

.toc-header {
  margin-bottom: 30px;
}

/* 内容区域样式 */
.section {
  margin: 20px 0;
  padding: 10px 0;
  page-break-inside: avoid;
}

.appendix {
  margin-top: 30px;
  padding: 10px 0;
  page-break-inside: avoid;
}

/* 表格样式 */
.summary-table table,
.metrics-table table,
.trades-table table,
.profit-table table,
.winning-stocks table {
  width: 100%;
  border-collapse: collapse;
}

.summary-table th,
.summary-table td,
.metrics-table th,
.metrics-table td,
.trades-table th,
.trades-table td,
.profit-table th,
.profit-table td,
.winning-stocks th,
.winning-stocks td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.summary-table th,
.metrics-table th,
.trades-table th,
.profit-table th,
.winning-stocks th {
  background-color: #f2f2f2;
  font-weight: bold;
}

/* 分页符 */
.page-break {
  page-break-after: always;
  margin: 20px 0;
}

/* PDF打印样式 */
@page {
  @top-center {
    content: element(header);
  }
  margin: 80px 20px 80px 20px;
}

@media print {
  .pdf-report-container {
    width: 100%;
    padding: 0;
  }

  .page-break {
    page-break-after: always;
    margin: 0;
  }

  .running-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 60px;
  }
}
</style>
