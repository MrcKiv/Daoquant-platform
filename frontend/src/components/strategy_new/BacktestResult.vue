<template>
  <div class="backtest-result p-6 bg-gradient-to-b from-gray-900 to-gray-800 text-white rounded-xl shadow-xl">
    <!-- 回测结果概览 -->
    <h2 class="text-2xl font-bold mb-6 border-b border-gray-600 pb-2">📊 回测结果概览</h2>

    <div class="mb-8 overflow-x-auto">
      <table class="w-full text-left text-gray-300 border-collapse">
        <thead class="bg-gray-700 text-gray-200">
          <tr>
            <th class="px-4 py-2 border border-gray-500">指标</th>
            <th class="px-4 py-2 border border-gray-500">值</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in summary" :key="i" class="hover:bg-gray-700">
            <td class="px-4 py-2 border border-gray-600">{{ item.label }}</td>
            <td class="px-4 py-2 border border-gray-600 font-semibold text-white">{{ item.value }}</td>
          </tr>
        </tbody>
      </table>
    </div>


<!--    <div id="pdf-content" ref="pdfContent" style="position: absolute; left: -9999px; background: white; width: 800px;">-->
<!--      <h1>回测报告</h1>-->
<!--      <table>{{ summary }}</table>-->
<!--&lt;!&ndash;      <div id="chart-container" style="width: 800px; height: 400px;"></div>&ndash;&gt;-->
<!--    </div>-->

<!--    &lt;!&ndash; 导出按钮 &ndash;&gt;-->
<!--    <button @click="generatePDF">导出 PDF</button>-->
  </div>


</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import html2pdf from 'html2pdf.js'
// import html2canvas from 'html2canvas'
import { computed } from 'vue'
import PdfReportGenerator from "@/components/strategy_new/PdfReportGenerator.vue";

const chartRef = ref(null)
const pdfContent = ref(null)
const chartContainer = ref(null)
const chartScreenshot = ref(null)

const props = defineProps({
  params: {
    type: Object,
    required: true,
    default: () => ({
      strategy: {},
      selector: {},
      factor: {}
    })
  }
})

const summary = computed(() => {
  const s = props.params.strategy
  const f = props.params.factor?.received_data?.factors || []
  const sel = props.params.selector?.received_data?.conditions[0] || {}

  const factorStr = f.map(item => `${item.name}${item.operator}${item.value}`).join('、')

  return [
    { label: '初始资金', value: `${s.capital}万元` },
    { label: '持股比例', value: `${s.ratio}%` },
    { label: '持股数目', value: `${s.hold}只` },
    { label: '收益基准', value: s.benchmark || '-' },
    { label: '时间范围', value: `${s.start_date} 至 ${s.end_date}` },
    { label: '选股范围', value: `板块(${s.scope})、风格(${s.scope})、行业(${s.scope})` },
    { label: '因子', value: factorStr || '-' },
    { label: '因子合成', value: sel.operator || '-' }
  ]
})

const trades = [
  { date: '2025-02-25', code: '000001', price: 10.2, amount: 1000, total: 10200, side: '买入' },
  { date: '2025-02-28', code: '000001', price: 11.5, amount: 1000, total: 11500, side: '卖出' }
]

const showDetail = (row) => {
  alert(`交易详情：\n股票代码：${row.code}\n交易金额：${row.total}`)
}




// const generatePDF = async () => {
//   // 等待 DOM 更新
//   await nextTick()
//
//   if (!pdfContent.value) {
//     console.error('PDF 内容容器未找到')
//     return
//   }
//
//   if (typeof html2pdf === 'undefined') {
//     console.error('html2pdf.js 未正确加载')
//     return
//   }
//
//   const opt = {
//     margin: 1,
//     filename: '回测报告.pdf',
//     image: { type: 'jpeg', quality: 0.98 },
//     html2canvas: { scale: 2 },
//     jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' },
//     output: 'dataurlnewwindow'
//   }
//
//   html2pdf().set(opt).from(pdfContent.value).save()
// }

</script>


<style scoped>
.table-auto th,
.table-auto td {
  text-align: center;
}
.border-collapse {
  border-collapse: collapse;
}

/* 单元格边框 */
.border {
  border: 1px solid #4b5563; /* gray-700 */
}

/* 表头单元格边框更浅一些 */
.border-gray-500 {
  border-color: #6b7280;
}

/* 内容行边框 */
.border-gray-600 {
  border-color: #4b5563;
}

/* PDF 内容样式 */
#pdf-content {
  padding: 20px;
  color: #000;
  background: #fff;
}

#pdf-content h1,
#pdf-content h2 {
  color: #000;
}

#pdf-content table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

#pdf-content th,
#pdf-content td {
  border: 1px solid #999;
  padding: 8px;
  text-align: left;
}

#pdf-content th {
  background-color: #f2f2f2;
}

#chart-container {
  width: 100%;
  height: 300px;
  background: #fff;
}
</style>

