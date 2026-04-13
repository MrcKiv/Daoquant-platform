<template>
  <section class="ai-feature-section">
    <h2 class="section-title">全心专注AI量化服务</h2>
    <div class="feature-grid">
      <div v-for="(item, index) in features" :key="index" class="feature-item">
        <img :src="item.icon" :alt="item.title" class="feature-icon" />
        <h3 class="feature-title">{{ item.title }}</h3>
        <p class="feature-description">{{ item.description }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
const features = [
  {
    icon: '/images/common/icons1.png',
    title: '人工智能核心平台',
    description: '企业级AI底层平台，量化交易领先算法，自动机器学习、超参优化，极速提高AI量化处理效率'
  },
  {
    icon: '/images/common/icons2.png',
    title: 'PB级量化数据',
    description: 'PB级量化专有海量金融数据+新型投资大数据，支持各类数据定制，满足不同投资需求'
  },
  {
    icon: '/images/common/icons3.png',
    title: '海量因子库',
    description: '2000+基础因子库，AI支持挖掘更多衍生因子，先人一步，发现更多市场机会'
  },
  {
    icon: '/images/common/icons4.png',
    title: '因子构建与分析',
    description: '表达式引擎创建多样因子库，支持对因子进行全方位分析，更快洞见有效因子'
  },
  {
    icon: '/images/common/icons5.png',
    title: '可视化开发环境',
    description: '模块化的可视化开发环境，与Python代码无缝集成，提高策略开发效率'
  },
  {
    icon: '/images/common/icons6.png',
    title: '高级优化',
    description: '超参搜索，组合优化器、滚动训练、归因分析等，高阶策略的自定义装置'
  }
]
</script>

<style>
@import '@/assets/css/common/Six.css';
</style>
