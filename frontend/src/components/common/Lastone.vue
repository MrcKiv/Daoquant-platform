<template>
  <footer class="footer">
    <div class="footer-container">
      <!-- 左侧三栏 -->
      <div class="footer-columns">
           <div class="column">
            <h6>关于 DaoQuant</h6>
            <router-link to="/about">关于我们</router-link>
            <router-link to="/join">加入我们</router-link>
            <router-link to="/contact">商务合作</router-link>
            <router-link to="/company">量道科技</router-link>
            <router-link to="/terms">用户条款</router-link>
            <router-link to="/privacy">隐私协议</router-link>
          </div>
          <div class="column">
            <h6>帮助与支持</h6>
            <router-link to="/guide">新手入门</router-link>
            <router-link to="/faq">常见问题</router-link>
            <router-link to="/academy">量化学院</router-link>
            <router-link to="/docs">文档</router-link>
          </div>
          <div class="column">
            <h6>关注我们</h6>
      
            <a href="https://www.douyin.com/" target="_blank">抖音</a>
            <a href="https://space.bilibili.com/" target="_blank">B站</a>
            <a href="https://www.zhihu.com/" target="_blank">知乎</a>
            <a href="https://weibo.com/" target="_blank">微博</a>
          </div>
        </div>

      <!-- 右侧二维码 -->
      <div class="qrcode-group">
        <div class="qrcode">
          <img src="/images/erweima/logo1.png" alt="微信公众号" />
          <p>微信公众号</p>
        </div>
        <div class="qrcode">
          <img src="/images/erweima/logo2.png" alt="微信客服" />
          <p>微信客服</p>
        </div>
        <div class="qrcode">
          <img src="/images/erweima/logo3.png" alt="用户QQ群" />
          <p>用户QQ群</p>
        </div>
      </div>
    </div>
     <!-- 底部版权 -->
    <div class="footer-bottom">
      ©2025 DaoQuant.com - 晋ICP备16017083号-1
    </div>
  </footer>
</template>

<style>
@import '@/assets/css/common/Lastone.css';
</style>
