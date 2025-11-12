import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import NProgress from 'nprogress'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/',
    component: () => import('@/layouts/TaskSchedulerLayout.vue'),
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: {
          title: '仪表板'
        }
      },
      // 任务管理路由
      {
        path: 'tasks',
        children: [
          {
            path: 'list',
            name: 'TaskList',
            component: () => import('@/views/tasks/List.vue'),
            meta: {
              title: '任务列表'
            }
          },
          {
            path: 'create',
            name: 'TaskCreate',
            component: () => import('@/views/tasks/Create.vue'),
            meta: {
              title: '创建任务'
            }
          },
          {
            path: 'statistics',
            name: 'TaskStatistics',
            component: () => import('@/views/tasks/Statistics.vue'),
            meta: {
              title: '任务统计'
            }
          }
        ]
      },
      // 监控中心路由
      {
        path: 'monitor',
        children: [
          {
            path: 'executions',
            name: 'Executions',
            component: () => import('@/views/monitor/Executions.vue'),
            meta: {
              title: '执行记录'
            }
          },
          {
            path: 'performance',
            name: 'Performance',
            component: () => import('@/views/monitor/Performance.vue'),
            meta: {
              title: '性能监控'
            }
          }
        ]
      },
      // 系统设置路由
      {
        path: 'settings',
        children: [
          {
            path: 'configuration',
            name: 'Configuration',
            component: () => import('@/views/settings/Configuration.vue'),
            meta: {
              title: '系统配置'
            }
          },
          {
            path: 'logs',
            name: 'SystemLogs',
            component: () => import('@/views/settings/Logs.vue'),
            meta: {
              title: '系统日志'
            }
          }
        ]
      }
    ]
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
    document.title = `${to.meta.title} - Task Scheduler`
  }

  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router