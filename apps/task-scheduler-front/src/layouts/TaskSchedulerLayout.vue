<template>
  <div class="layout-container">
    <!-- 顶部导航栏 -->
    <el-header class="layout-header">
      <div class="header-left">
        <el-button
          :icon="Expand"
          text
          @click="toggleCollapse"
          class="collapse-btn"
        />
        <h1 class="header-title">Task Scheduler</h1>
      </div>
      <div class="header-right">
        <el-badge :value="3" class="notification-badge">
          <el-button :icon="Bell" text circle />
        </el-badge>
        <el-dropdown>
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>个人设置</el-dropdown-item>
              <el-dropdown-item divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container class="layout-content">
      <!-- 侧边栏 -->
      <el-aside :width="isCollapse ? '64px' : '240px'" class="layout-sidebar">
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :unique-opened="true"
          router
          class="sidebar-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Monitor /></el-icon>
            <template #title>仪表板</template>
          </el-menu-item>

          <!-- 任务管理 -->
          <el-sub-menu index="/tasks">
            <template #title>
              <el-icon><List /></el-icon>
              <span>任务管理</span>
            </template>
            <el-menu-item index="/tasks/list">
              <el-icon><Document /></el-icon>
              <template #title>任务列表</template>
            </el-menu-item>
            <el-menu-item index="/tasks/create">
              <el-icon><Plus /></el-icon>
              <template #title>创建任务</template>
            </el-menu-item>
            <el-menu-item index="/tasks/statistics">
              <el-icon><DataAnalysis /></el-icon>
              <template #title>任务统计</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 监控中心 -->
          <el-sub-menu index="/monitor">
            <template #title>
              <el-icon><View /></el-icon>
              <span>监控中心</span>
            </template>
            <el-menu-item index="/monitor/executions">
              <el-icon><Clock /></el-icon>
              <template #title>执行记录</template>
            </el-menu-item>
            <el-menu-item index="/monitor/performance">
              <el-icon><TrendCharts /></el-icon>
              <template #title>性能监控</template>
            </el-menu-item>
          </el-sub-menu>

          <!-- 系统设置 -->
          <el-sub-menu index="/settings">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </template>
            <el-menu-item index="/settings/configuration">
              <el-icon><Tools /></el-icon>
              <template #title>系统配置</template>
            </el-menu-item>
            <el-menu-item index="/settings/logs">
              <el-icon><Document /></el-icon>
              <template #title>系统日志</template>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Monitor,
  List,
  Document,
  Plus,
  DataAnalysis,
  View,
  Clock,
  TrendCharts,
  Setting,
  Tools,
  Bell,
  Expand
} from '@element-plus/icons-vue'

// 响应式数据
const isCollapse = ref(false)
const route = useRoute()
const router = useRouter()

// 计算当前激活的菜单项
const activeMenu = computed(() => route.path)

// 切换侧边栏折叠状态
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 处理菜单选择
const handleMenuSelect = (index: string) => {
  router.push(index)
}

// 组件挂载时初始化
onMounted(() => {
  console.log('Task Scheduler Layout mounted')
})
</script>

<style lang="scss" scoped>
.layout-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.layout-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      font-size: 18px;
      color: #606266;

      &:hover {
        color: #409eff;
      }
    }

    .header-title {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      margin: 0;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;

    .notification-badge {
      margin-right: 8px;
    }
  }
}

.layout-content {
  flex: 1;
  overflow: hidden;
}

.layout-sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  transition: width 0.3s ease;
  overflow: hidden;

  .sidebar-menu {
    height: 100%;
    border-right: none;

    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      height: 48px;
      line-height: 48px;
      font-size: 14px;

      .el-icon {
        width: 16px;
        height: 16px;
        margin-right: 8px;
      }
    }

    :deep(.el-menu--collapse) {
      .el-menu-item,
      .el-sub-menu__title {
        padding: 0 20px;
      }
    }

    :deep(.el-sub-menu .el-menu-item) {
      background-color: #f8f9fa;
      padding-left: 48px !important;

      &:hover {
        background-color: #ecf5ff;
      }

      &.is-active {
        background-color: #ecf5ff;
        color: #409eff;
        font-weight: 500;
      }
    }
  }
}

.layout-main {
  background: #f5f5f5;
  padding: 20px;
  overflow-y: auto;
}

// 响应式设计
@media (max-width: 768px) {
  .layout-header {
    padding: 0 16px;

    .header-left .header-title {
      font-size: 18px;
    }
  }

  .layout-sidebar {
    position: absolute;
    top: 60px;
    left: 0;
    bottom: 0;
    z-index: 999;
    box-shadow: 2px 0 6px rgba(0, 21, 41, 0.1);
  }

  .layout-main {
    padding: 16px;
  }
}
</style>