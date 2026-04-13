import { watchEffect } from 'vue'
import * as echarts from 'echarts'

export function useKlineChart(chartRef, data, title = 'K线图') {
  let timer = null

  const upColor = '#00da3c'
  const downColor = '#ec0000'

  const option = {
    title: {
      text: title,
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 'bold' }
    },
    backgroundColor: '#fff',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      borderWidth: 1,
      borderColor: '#ccc',
      padding: 10,
      backgroundColor: 'rgba(255,255,255,0.9)',
      textStyle: { color: '#000' }
    },
    xAxis: {
      type: 'category',
      data: data.dates,
      scale: true,
      boundaryGap: true,
      axisLine: { onZero: false },
      splitLine: { show: false },
      axisLabel: { rotate: 45 },
      min: 'dataMin',
      max: 'dataMax'
    },
    yAxis: {
      scale: true,
      splitArea: { show: true }
    },
    grid: { left: '5%', right: '5%', bottom: '15%' },
    dataZoom: [
      { type: 'inside', start: 80, end: 100 },
      { show: true, type: 'slider', top: '90%', start: 80, end: 100 }
    ],
    series: [
      {
        type: 'candlestick',
        name: 'K线图',
        data: data.values,
        itemStyle: {
          color: upColor,
          color0: downColor,
          borderColor: upColor,
          borderColor0: downColor
        },
        tooltip: {
          formatter: function (param) {
            const d = param.data
            return [
              `开盘: ${d[0]}`,
              `收盘: ${d[1]}`,
              `最低: ${d[2]}`,
              `最高: ${d[3]}`
            ].join('<br/>')
          }
        }
      }
    ]
  }

  watchEffect(() => {
    if (!chartRef.value || !data?.dates?.length || !data?.values?.length) return

    // 延迟执行，确保 DOM 渲染完成
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      const existing = echarts.getInstanceByDom(chartRef.value)
      if (existing) existing.dispose()

      const chart = echarts.init(chartRef.value)
      chart.setOption(option)
      chart.resize()
      window.addEventListener('resize', () => chart.resize())
    }, 200)
  })
}
