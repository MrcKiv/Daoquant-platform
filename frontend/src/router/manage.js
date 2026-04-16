export default [
  {
    path: '/manage/login',
    name: 'ManageLogin',
    component: () => import('@/views/manage/Login.vue')
  },
  {
    path: '/manage/users',
    name: 'ManageUsers',
    component: () => import('@/views/manage/Users.vue'),
    meta: {
      requiredLevel: 'admin',
      loginPath: '/manage/login'
    }
  }
]
