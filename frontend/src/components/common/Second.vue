<template>
  <section class="ck-slide">
    <div class="jq-banner">
      <div class="banner-info">
        <div class="banner-info-head">量化投研, 从量道开始</div>
        <div class="banner-info-text">我们提供免费的量化策略、投研工具、最先进的股票诊断、在线交流社区</div>
        <div class="banner-info-login" v-if="!userStore.isLoggedIn">
          <router-link to="/register" class="banner-register">立即注册</router-link>
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
