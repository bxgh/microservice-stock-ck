import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import NProgress from 'nprogress'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: {
      title: '首页'
    }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/index.vue'),
    meta: {
      title: '仪表板'
    }
  },
  {
    path: '/components',
    name: 'Components',
    component: () => import('@/views/components/index.vue'),
    meta: {
      title: '组件库'
    }
  },
  {
    path: '/examples',
    name: 'Examples',
    component: () => import('@/views/examples/index.vue'),
    meta: {
      title: '使用示例'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫
router.beforeEach((to, from, next) => {
  NProgress.start()

  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - Frontend Template`
  }

  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router