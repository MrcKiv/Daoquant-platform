export default [
  { path: '/strategy-dev', component: () => import('@/views/strategy/strategy-develop.vue') },
  { path: '/NewStrategy',
    component: () => import('@/views/strategy/NewStrategy.vue') ,
     meta: { requiredLevel: 'basic' }
  },

  {
    path: '/StrategyDetail/:id',
    name: 'StrategyDetail',
    component: () => import('@/views/strategy/strategy-new.vue')
  },
    {
    path: '/strategyConfig/:id',
    name: 'StrategyConfig',
    component: () => import('@/views/strategy/strategy-new.vue')
  },
    {
  path: '/Strategy-detail/:id',
  name: 'strategyDetail',
  component: () => import('@/components/strategy_new/strategyDetail.vue')
},
  { path: '/strategy-ai', component: () => import('@/views/strategy/strategy-ai.vue') },
  { path: '/strategy-famous', component: () => import('@/views/strategy/strategy-famous.vue') },
  { path: '/strategy-forum', component: () => import('@/views/strategy/strategy-forum.vue') },
  { path: '/strategy-mall', component: () => import('@/views/strategy/strategy-mall.vue') },
  { path: '/strategy-simulation', component: () => import('@/views/strategy/strategy-simulation.vue') },
  { path: '/strategy-similar', component: () => import('@/views/strategy/strategy-similar.vue') },
     // ✅ 添加 PDF 报告页面路由
  { path: '/strategy/report', component: () =>  import('@/components/strategy_new/BacktestReportFixed.vue') },
]
