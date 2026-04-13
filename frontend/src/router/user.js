export default [
  { path: '/register', component: () => import('@/views/user/Register.vue') },
  { path: '/login', component: () => import('@/views/user/login.vue') },
  { path: '/reset', component: () => import('@/views/user/reset.vue') },
  { path: '/user-strategy', component: () => import('@/views/user/user-strategy.vue') },
]
