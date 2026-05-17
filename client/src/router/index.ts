import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import Home from '../views/Home/Home.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: Home,
    meta: { requiresAuth: false }
  },
  {
    path: '/DocGen',
    name: 'docgen',
    component: () => import('../views/Doc.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/DRG',
    name: 'drg',
    component: () => import('../views/DRG/DRG.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/auth',
    name: 'auth',
    component: () => import('../views/Auth/AuthPage.vue'),
    meta: { requiresGuest: true }
  }
]

const router = createRouter({
  history: createWebHistory('/'),
  routes
})

// 新版路由守卫 - 不使用回调
router.beforeEach((to, from) => {
  const token = localStorage.getItem('access_token')
  const isLoggedIn = !!token
  
  // 需要登录但未登录 → 去登录页
  if (to.meta.requiresAuth && !isLoggedIn) {
    return { path: '/auth', query: { redirect: to.fullPath } }
  }
  
  // 已登录且要访问登录页 → 去首页
  if (to.meta.requiresGuest && isLoggedIn) {
    return '/'
  }
  
  // 正常放行
  return true
})

export default router