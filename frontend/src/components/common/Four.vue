<template>
  <div class="spark-banner-wrapper">
    <div
      class="spark-banner"
      @click="navigateTo(currentIndex)"
      @mouseenter="pauseRotation"
      @mouseleave="resumeRotation"
    >
      <img :src="banners[currentIndex].image" alt="banner" class="banner-img" />
      <div class="banner-overlay">
        <h2 class="banner-title">{{ banners[currentIndex].title }}</h2>
        <p class="banner-sub">{{ banners[currentIndex].subtitle }}</p>
      </div>
    </div>

    <div class="dot-group" @mouseenter="pauseRotation" @mouseleave="resumeRotation">
      <span
        v-for="(banner, index) in banners"
        :key="index"
        :class="['dot', { active: index === currentIndex }]"
        @click="currentIndex = index"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const banners = [
  {
    image: '/images/common/lbt1.jpg',
    title: 'DaoQuant 星火计划',
    subtitle: '邀请好友，一起领币，赚佣金',
    route: '/spark/plan'
  },
  {
    image: '/images/common/lbt2.jpg',
    title: '量化交易入门课',
    subtitle: '系统学习五大步骤，掌握交易实战',
    route: '/course/intro'
  },
  {
    image: '/images/common/lbt3.jpg',
    title: '策略平台全新升级',
    subtitle: '更强工具，更易用编辑器，助力交易',
    route: '/platform/update'
  }
]

const currentIndex = ref(0)
let timer = null

const startRotation = () => {
  timer = setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % banners.length
  }, 2000)
}

const pauseRotation = () => {
  clearInterval(timer)
}

const resumeRotation = () => {
  startRotation()
}

onMounted(() => {
  startRotation()
})

onUnmounted(() => {
  clearInterval(timer)
})

const navigateTo = (index) => {
  router.push(banners[index].route)
}
</script>


<style >
  @import '@/assets/css/common/Four.css';
</style>
