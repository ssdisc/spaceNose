/**
 * Vue Router 配置
 * 星际嗅探者 - 多页面路由管理
 */

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/GroundLab.vue'),
    meta: { title: '地面验证实验台' }
  },
  {
    path: '/visualization',
    name: 'DataVisualization',
    component: () => import('../views/DataVisualization.vue'),
    meta: { title: '数据监控' }
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL || '/'),
  routes
})

// 导航守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - 星际嗅探者`
  }
  next()
})

export default router
