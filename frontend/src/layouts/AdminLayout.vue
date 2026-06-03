<script setup lang="ts">
import { computed, defineComponent, h, resolveComponent, type PropType, type VNode } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { routes } from '../router'

type MenuRoute = RouteRecordRaw & { children?: MenuRoute[] }

const joinPath = (basePath: string, path: string) => {
  if (path.startsWith('/')) {
    return path
  }
  const normalizedBase = basePath.endsWith('/') ? basePath.slice(0, -1) : basePath
  return `${normalizedBase}/${path}`.replace(/\/+/g, '/')
}

const buildMenuTree = (items: MenuRoute[], basePath = ''): MenuRoute[] =>
  items
    .map((item) => {
      const fullPath = joinPath(basePath || '', item.path)
      const children = item.children ? buildMenuTree(item.children as MenuRoute[], fullPath) : []
      return {
        ...item,
        path: fullPath,
        children,
      } as MenuRoute
    })
    .filter((item) => item.meta?.isMenu || (item.children && item.children.length > 0))

const menuTree = computed(() => buildMenuTree(routes as MenuRoute[]))
const route = useRoute()
const breadcrumbItems = computed(() =>
  route.matched
    .filter((item) => Boolean(item.meta?.title))
    .map((item) => ({
      title: item.meta?.title as string,
      path: item.path,
    })),
)

const MenuTree = defineComponent({
  name: 'MenuTree',
  props: {
    items: {
      type: Array as PropType<MenuRoute[]>,
      required: true,
    },
  },
  setup(props) {
    const ElSubMenu = resolveComponent('ElSubMenu')
    const ElMenuItem = resolveComponent('ElMenuItem')

    const renderIcon = (svg?: unknown) => {
      if (typeof svg !== 'string' || !svg.trim()) {
        return null
      }
      return h('span', {
        class: 'menu-icon',
        innerHTML: svg,
      })
    }

    const renderMenu = (item: MenuRoute) => {
      const title = () => {
        const titleChildren: VNode[] = [
          h('span', { class: 'menu-label' }, String(item.meta?.title || item.name || item.path)),
        ]
        const iconNode = renderIcon(item.meta?.icon)
        if (iconNode) {
          titleChildren.unshift(iconNode)
        }
        return h('span', { class: 'menu-title' }, titleChildren)
      }
      const hasChildren = Boolean(item.children?.length)
      if (hasChildren) {
        return h(
          ElSubMenu,
          { index: item.path },
          {
            title,
            default: () => item.children!.map((child) => renderMenu(child)),
          },
        )
      }
      return h(
        ElMenuItem,
        { index: item.path },
        {
          default: title,
        },
      )
    }

    return () => props.items.map((item) => renderMenu(item))
  },
})
</script>

<template>
  <el-container class="layout-root">
    <el-aside width="220px" class="aside">
      <div class="brand">Screen RPA</div>
      <el-menu router :default-active="$route.path" class="menu">
        <MenuTree :items="menuTree" />
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item
            v-for="(item, index) in breadcrumbItems"
            :key="item.path"
            :to="index < breadcrumbItems.length - 1 ? item.path : undefined"
          >
            {{ item.title }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </el-header>
      <el-main class="main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-root {
  min-height: 100vh;
}
.aside {
  border-right: 1px solid var(--el-border-color);
}
.brand {
  padding: 20px 16px;
  height: 60px;
  font-weight: 600;
  font-size: 16px;
  border-bottom: 1px solid var(--el-border-color);
}
.menu {
  border-right: none;
}
.menu :deep(.menu-title) {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.menu :deep(.menu-icon) {
  width: 14px;
  height: 14px;
  display: inline-flex;
  color: currentColor;
  flex: 0 0 14px;
}
.menu :deep(.menu-icon svg) {
  width: 100%;
  height: 100%;
  display: block;
}
.header {
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color);
}
.header :deep(.el-breadcrumb__inner) {
  font-size: 15px;
  color: var(--el-text-color-regular);
}
.main {
  padding: 0 !important;
  background: var(--el-fill-color-lighter);
  max-height: calc(100vh - 60px);
  overflow-y: auto;
  
}
</style>
