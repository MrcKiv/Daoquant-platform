<template>
  <section class="ck-slide">
    <div class="jq-banner">
      <div class="banner-info">
        <div class="banner-info-head">量化投研, 从内部自用开始</div>
        <div class="banner-info-text">我们提供量化策略与投研工具，帮助团队更高效地完成策略开发、回测与复盘分析</div>
        <div class="banner-info-login" v-if="!userStore.isLoggedIn">
          <router-link to="/login" class="banner-login">登录</router-link>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
  import { useUserStore } from '@/stores/user'
  const userStore = useUserStore()
</script>

<style >
  @import '@/assets/css/common/Second.css';
</style>
