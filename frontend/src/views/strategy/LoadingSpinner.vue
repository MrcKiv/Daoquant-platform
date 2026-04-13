<template>
  <div class="spinner">
    <div class="dot"></div>
    <div class="dot"></div>
    <div class="dot"></div>
  </div>
</template>

<script setup>
defineOptions({
  name: 'LoadingSpinner'
})
</script>

<style scoped>
.spinner {
  display: inline-flex;
  gap: 6px;
  height: 24px;
  align-items: center;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: bounce 1.4s infinite ease-in-out;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-10px); }
}
</style>