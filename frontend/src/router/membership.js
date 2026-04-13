// router/membership.js
export default [
  {
    path: '/upgrade',
    name: 'Upgrade',
    component: () => import('@/views/membership/Upgrade.vue'),
    meta: { requiredLevel: 'free' } // 任何人都可以访问升级页面
  },
  {
    path: '/membership/upgrade',
    name: 'MembershipUpgrade',
    component: () => import('@/views/membership/Upgrade.vue'),
    meta: { requiredLevel: 'free' }
  }
]
