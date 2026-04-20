export default [
  {
    path: '/stock-data-backfill',
    component: () => import('@/views/stock/StockDataBackfill.vue'),
    meta: { requiredLevel: 'admin' }
  }
]
