import { ref, nextTick } from 'vue'
import html2pdf from 'html2pdf.js'
import * as echarts from 'echarts'

export function useGeneratePDF(options = {}) {
  const {
    containerId = 'pdf-container',
    filename = 'report',
    format = 'a4',
    orientation = 'portrait',
    margin = [10, 5, 10, 5],
    scale = 2,
    useNativePrint = false,
    chartData = [],
    onBeforeExport = () => {},
    onAfterExport = () => {},
  } = options

  const isGenerating = ref(false)
  const pdfContentHtml = ref('')
  const chartInstances = ref([])

  const initPdfChart = () => {
    chartData.forEach(({ id, option }) => {
      const container = document.getElementById(id)
      if (!container) return
      const chart = echarts.init(container)
      chart.setOption(option)
      chartInstances.value.push(chart)
    })
  }

  const disposePdfCharts = () => {
    chartInstances.value.forEach(chart => {
      if (chart && !chart.isDisposed()) {
        chart.dispose()
      }
    })
    chartInstances.value = []
  }

  const generatePDF = async () => {
    isGenerating.value = true
    onBeforeExport()

    try {
      if (useNativePrint) {
        await nextTick()
        if (document.fonts?.ready) {
          await document.fonts.ready
        }
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
        await new Promise(resolve => setTimeout(resolve, 800))
        alert('请在打印面板中选择“另存为 PDF / Save as PDF”，不要选择“Microsoft Print to PDF”，否则长报告可能生成损坏文件。')
        window.print()
        return
      }

      await nextTick()
      if (document.fonts?.ready) {
        await document.fonts.ready
      }
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
      await new Promise(resolve => setTimeout(resolve, 1000))

      initPdfChart()
      await new Promise(resolve => setTimeout(resolve, 500))

      const element = document.getElementById(containerId)
      if (!element) {
        console.error('PDF 容器未找到')
        alert('PDF 容器未找到，请检查 ID 是否正确')
        return
      }

      const opt = {
        margin,
        filename: `${filename}.pdf`,
        image: { type: 'jpeg', quality: 0.92 },
        html2canvas: {
          scale,
          useCORS: true,
          backgroundColor: '#ffffff',
          scrollX: 0,
          scrollY: 0,
          windowWidth: element.scrollWidth || element.offsetWidth || document.documentElement.clientWidth,
          windowHeight: element.scrollHeight || element.offsetHeight || document.documentElement.clientHeight,
        },
        jsPDF: { unit: 'mm', format, orientation },
        pagebreak: { mode: ['css', 'legacy'] },
      }

      await html2pdf().set(opt).from(element).save()
    } catch (error) {
      console.error('生成 PDF 失败:', error)
      alert('生成 PDF 失败，请重试')
    } finally {
      disposePdfCharts()
      isGenerating.value = false
      onAfterExport()
    }
  }

  return {
    isGenerating,
    pdfContentHtml,
    initPdfChart,
    generatePDF,
  }
}
