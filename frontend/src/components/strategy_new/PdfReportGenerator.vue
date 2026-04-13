<template>
  <div>
    <!-- 强制渲染插槽内容 -->
    <div :id="containerId" ref="pdfContent" class="pdf-content" style="width: 800px; margin: 0 auto; padding: 20px; background: white; border: 1px solid #ccc;">
      <slot name="content">
      </slot>
    </div>

    <!-- 导出按钮 -->
    <button @click="generatePDF">{{ buttonText }}</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import html2pdf from 'html2pdf.js'
import { nextTick } from 'vue'

const props = defineProps({
  buttonText: String,
  filename: String,
  containerId: {
    type: String,
    default: () => `pdf-container-${Math.random().toString(36).substr(2, 9)}`
  }
})

const pdfContent = ref(null)

const generatePDF = async () => {
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 200)) // 等待渲染完成
  console.log('pdfContent.value:', pdfContent.value)

  const opt = {
    margin: 1,
    filename: props.filename + '.pdf',
    image: {type: 'jpeg', quality: 0.98},
    html2canvas: {scale: 2},
    jsPDF: {unit: 'in', format: 'a3', orientation: 'portrait'}
  }

  if (pdfContent.value) {
    html2pdf().set(opt).from(pdfContent.value).save()
  } else {
    console.error('PDF 内容容器未找到')
  }
}
</script>

<style scoped>
.pdf-content {
  //position: absolute !important;
  //left: -9999px !important;
  top: 0 !important;
  width: 800px !important;
  background: white !important;
  color: black !important;
  padding: 20px !important;
}
</style>
