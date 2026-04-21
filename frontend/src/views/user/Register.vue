<template>
  <FixedNavbar />
  <div class="auth-bg">
    <div class="auth-card">
      <h2 class="title">注册已关闭</h2>
      <p class="closed-text">当前系统不开放自助注册，请联系管理员创建账号。</p>

      <p class="links">
        已有账号或已开通账号？
        <router-link to="/login" class="btn-outline">立即登录</router-link>
      </p>
      <p class="forgot">
        <router-link to="/manage/login">管理员登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import FixedNavbar from '@/components/common/FixedNavbar.vue'
</script>

<style scoped>
@import '@/assets/css/user/Register.css';

.closed-text {
  margin: 16px 0 24px;
  color: #666;
  line-height: 1.8;
  text-align: center;
}
</style>
