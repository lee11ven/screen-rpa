import { createRouter, createWebHistory, RouterView } from 'vue-router'

export const routes = [
  {
    path: 'workflow',
    name: 'business-execution',
    component: RouterView,
    redirect: '/workflow/index',
    meta: {
      title: '业务执行',
      isMenu: true,
      icon: '<svg viewBox="0 0 24 24" fill="none"><path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    },
    children: [
      {
        path: 'index',
        name: 'workflow-list',
        component: () => import('@/modules/workflow/pages/WorkflowListPage.vue'),
        meta: {
          title: '流程列表',
          isMenu: true,
          icon: '<svg viewBox="0 0 24 24" fill="none"><rect x="5" y="5" width="14" height="14" rx="2" stroke="currentColor" stroke-width="2"/><path d="M8 9h8M8 13h8M8 17h5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
        },
      },
      {
        path: 'global-config',
        name: 'workflow-global-config',
        component: () => import('@/modules/workflow/pages/GlobalObjectConfigPage.vue'),
        meta: {
          title: '全局对象配置',
          isMenu: true,
          icon: '<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="3.5" stroke="currentColor" stroke-width="2"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
        },
      },
      {
        path: 'queue',
        name: 'workflow-queue-list',
        component: () => import('@/modules/workflow/pages/QueueListPage.vue'),
        meta: {
          title: '执行队列列表',
          isMenu: true,
          icon: '<svg viewBox="0 0 24 24" fill="none"><rect x="4" y="5" width="16" height="4" rx="1.5" stroke="currentColor" stroke-width="2"/><rect x="4" y="10" width="16" height="4" rx="1.5" stroke="currentColor" stroke-width="2"/><rect x="4" y="15" width="10" height="4" rx="1.5" stroke="currentColor" stroke-width="2"/></svg>',
        },
      },
      {
        path: ':id/editor',
        name: 'workflow-editor',
        component: () => import('@/modules/workflow/pages/WorkflowEditorPage.vue'),
        props: true,
        meta: {
          title: '流程编辑',
          isMenu: false,
        },
      },
      {
        path: ':id/versions',
        name: 'workflow-versions',
        component: () => import('@/modules/workflow/pages/WorkflowVersionsPage.vue'),
        props: true,
        meta: {
          title: '版本管理',
          isMenu: false,
        },
      },
      {
        path: 'run/:runId',
        name: 'workflow-run',
        component: () => import('@/modules/workflow/pages/WorkflowRunDetailPage.vue'),
        props: true,
        meta: {
          title: '运行详情',
          isMenu: false,
        },
      },
    ],
  },
  {
    path: '/system-config',
    name: 'workflow-system-config',
    component: () => import('@/modules/workflow/pages/SystemConfigPage.vue'),
    meta: {
      title: '系统配置',
      isMenu: true,
      icon: '<svg viewBox="0 0 24 24" fill="none"><path d="M12 2.5L14.87 5.07L18.72 5.28L18.93 9.13L21.5 12L18.93 14.87L18.72 18.72L14.87 18.93L12 21.5L9.13 18.93L5.28 18.72L5.07 14.87L2.5 12L5.07 9.13L5.28 5.28L9.13 5.07Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/></svg>',
    },
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/AdminLayout.vue'),
      children: [
        { path: '', redirect: '/workflow' },
        ...routes,
      ],
    },
  ],
})

export default router
