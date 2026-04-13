<template>
  <div>
    <transition name="fade">
      <div
        v-if="visible"
        class="fixed top-0 right-0 w-96 h-full bg-gradient-to-b from-gray-900 to-gray-800 shadow-2xl z-50 p-6 overflow-y-auto text-white"
      >
        <div class="flex justify-between items-center mb-4 border-b border-gray-600 pb-2">
          <h3 class="text-xl font-bold">🗂️ 交易详情</h3>
          <button @click="close" class="text-gray-400 hover:text-white">✖</button>
        </div>
        <div v-if="detail" class="space-y-3 text-sm">
          <p><strong class="text-gray-400">股票代码：</strong>{{ detail.code }}</p>
          <p><strong class="text-gray-400">交易时间：</strong>{{ detail.date }}</p>
          <p><strong class="text-gray-400">交易类型：</strong>{{ detail.side }}</p>
          <p><strong class="text-gray-400">交易价格：</strong>{{ detail.price }}</p>
          <p><strong class="text-gray-400">交易数量：</strong>{{ detail.amount }}</p>
          <p><strong class="text-gray-400">成交额：</strong>{{ detail.total }}</p>
          <p><strong class="text-gray-400">盈利情况：</strong>{{ detail.profit ?? '—' }}</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  visible: Boolean,
  detail: Object
})

const emit = defineEmits(['close'])
const close = () => emit('close')
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
