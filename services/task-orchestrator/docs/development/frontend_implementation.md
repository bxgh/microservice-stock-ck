# Task Orchestrator 前端开发计划

**版本**: v1.0  
**创建时间**: 2026-01-14  
**负责人**: Frontend Team  
**预计工时**: 11 小时

---

## 一、开发目标

开发一个嵌入式 Dashboard Web 界面，提供以下功能：
1. **任务列表视图**：展示所有任务的状态、调度配置、下次运行时间
2. **任务控制面板**：手动触发、暂停、恢复任务
3. **执行历史查看器**：查看每个任务的历史执行记录
4. **DAG 依赖可视化**：图形化展示任务之间的依赖关系
5. **系统健康总览**：实时显示系统关键指标

---

## 二、技术栈

| 技术 | 版本 | 用途 | CDN |
|-----|------|------|-----|
| Vue 3 | 3.4+ | 前端框架 | `https://unpkg.com/vue@3/dist/vue.global.js` |
| Axios | 1.6+ | HTTP 请求 | `https://unpkg.com/axios/dist/axios.min.js` |
| Tailwind CSS | 3.4+ | UI 样式 | `https://cdn.tailwindcss.com` |
| Mermaid.js | 10+ | DAG 图表 | `https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js` |

**为什么使用 CDN？**
- ✅ 无需 Node.js 构建流程
- ✅ 单 HTML 文件部署
- ✅ 快速迭代原型

---

## 三、文件结构

```
services/task-orchestrator/
└── src/
    └── static/
        ├── dashboard.html       # 主 HTML 文件（包含 Vue 应用）
        ├── css/
        │   └── dashboard.css    # 自定义样式（可选）
        └── js/
            └── dashboard.js     # Vue 应用逻辑（可选分离）
```

**注**: 初期可以将 CSS 和 JS 全部内嵌在 `dashboard.html` 中，后续优化时再分离。

---

## 四、界面设计规范

### 4.1 布局结构

```
┌─────────────────────────────────────────────────────────────┐
│  顶部导航栏 (Header)                                         │
│  [Logo] Task Orchestrator Dashboard     [刷新] [重载配置]   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  系统健康卡片 (Overview Cards)                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                      │
│  │总任务 │ │已启用│ │运行中│ │今日失败│                      │
│  └──────┘ └──────┘ └──────┘ └──────┘                      │
│                                                               │
├───────────────────────────┬─────────────────────────────────┤
│                           │                                 │
│  任务列表 (左 60%)        │  右侧面板 (右 40%)              │
│  ┌─────────────────────┐  │  ┌───────────────────────────┐ │
│  │ 任务名称 | 类型 | ... │  │  │ Tab 1: 执行历史           │ │
│  │ ─────────────────── │  │  │ ─────────────────────────│ │
│  │ K线每日同步 | 工作流│  │  │ □ 2026-01-14 17:30 成功  │ │
│  │ ▶ ⏸ 📊             │  │  │ □ 2026-01-13 17:30 成功  │ │
│  │                     │  │  │                           │ │
│  │ 分笔数据采集 | Docker│  │  │ Tab 2: DAG 可视化        │ │
│  │ ▶ ⏸ 📊             │  │  │ ─────────────────────────│ │
│  └─────────────────────┘  │  │ [Mermaid 图表渲染区域]    │ │
│                           │  └───────────────────────────┘ │
├───────────────────────────┴─────────────────────────────────┤
│  底部状态栏 (Footer)                                         │
│  Scheduler: Running | Docker: OK | Last Updated: 10:42:30   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 配色方案

**主题**: 现代科技风（深色模式优先）

| 元素 | 颜色 | Tailwind Class |
|-----|------|----------------|
| 背景 | 深灰蓝 | `bg-gray-900` |
| 卡片 | 深灰 | `bg-gray-800` |
| 主色调 | 蓝色 | `blue-500` |
| 成功状态 | 绿色 | `green-500` |
| 失败状态 | 红色 | `red-500` |
| 警告状态 | 黄色 | `yellow-500` |
| 文本 | 浅灰 | `text-gray-100` |

---

## 五、核心功能实现

### 5.1 任务列表表格

**数据来源**: `GET /api/v1/tasks`

**表格列**:
| 列名 | 数据字段 | 宽度 | 功能 |
|-----|---------|------|-----|
| 任务名称 | `name` | 25% | 显示任务名称 |
| 类型 | `type` | 10% | Docker/HTTP/Workflow |
| 调度表达式 | `schedule.expression` | 15% | Cron 表达式 |
| 下次运行 | `next_run_time` | 15% | 格式化时间显示 |
| 状态 | `enabled` + `paused` | 10% | 徽章：已启用/已暂停/已禁用 |
| 操作 | - | 25% | 按钮：触发/暂停/查看历史 |

**Vue 代码示例**:
```vue
<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm text-left text-gray-300">
      <thead class="text-xs uppercase bg-gray-700">
        <tr>
          <th class="px-6 py-3">任务名称</th>
          <th class="px-6 py-3">类型</th>
          <th class="px-6 py-3">调度表达式</th>
          <th class="px-6 py-3">下次运行</th>
          <th class="px-6 py-3">状态</th>
          <th class="px-6 py-3">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.id" 
            class="border-b bg-gray-800 border-gray-700 hover:bg-gray-700">
          <td class="px-6 py-4 font-medium">{{ task.name }}</td>
          <td class="px-6 py-4">
            <span class="badge-type">{{ task.type }}</span>
          </td>
          <td class="px-6 py-4 font-mono text-xs">{{ task.schedule.expression }}</td>
          <td class="px-6 py-4">{{ formatTime(task.next_run_time) }}</td>
          <td class="px-6 py-4">
            <span :class="getStatusBadge(task)">{{ getStatusText(task) }}</span>
          </td>
          <td class="px-6 py-4 space-x-2">
            <button @click="triggerTask(task.id)" class="btn-primary">▶️ 触发</button>
            <button @click="togglePause(task)" class="btn-secondary">
              {{ task.paused ? '▶️ 恢复' : '⏸️ 暂停' }}
            </button>
            <button @click="showHistory(task.id)" class="btn-info">📊 历史</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  data() {
    return {
      tasks: []
    }
  },
  methods: {
    async fetchTasks() {
      const response = await axios.get('/api/v1/tasks');
      this.tasks = response.data;
    },
    async triggerTask(taskId) {
      await axios.post(`/api/v1/tasks/${taskId}/trigger`);
      this.$toast('任务已触发执行');
      this.fetchTasks(); // 刷新列表
    },
    async togglePause(task) {
      const endpoint = task.paused ? 'resume' : 'pause';
      await axios.post(`/api/v1/tasks/${task.id}/${endpoint}`);
      this.fetchTasks();
    },
    formatTime(timestamp) {
      if (!timestamp) return '-';
      return new Date(timestamp).toLocaleString('zh-CN');
    },
    getStatusBadge(task) {
      if (!task.enabled) return 'badge-disabled';
      if (task.paused) return 'badge-paused';
      return 'badge-enabled';
    }
  },
  mounted() {
    this.fetchTasks();
    // 每 30 秒刷新一次
    setInterval(this.fetchTasks, 30000);
  }
}
</script>
```

---

### 5.2 执行历史面板

**数据来源**: `GET /api/v1/tasks/{task_id}/history`

**显示内容**:
- 执行时间（开始、结束）
- 状态图标（✅ 成功、❌ 失败、⏱️ 超时）
- 耗时
- 错误信息（失败时展开显示）

**Vue 代码示例**:
```vue
<template>
  <div class="history-panel">
    <h3 class="text-lg font-bold mb-4">执行历史: {{ currentTask?.name }}</h3>
    
    <div v-if="loading" class="text-center py-8">
      <div class="spinner"></div>
    </div>
    
    <div v-else class="space-y-2">
      <div v-for="log in history" :key="log.id" 
           class="history-item p-3 rounded bg-gray-700">
        <div class="flex justify-between items-center">
          <div class="flex items-center space-x-3">
            <span class="status-icon">{{ getStatusIcon(log.status) }}</span>
            <span class="text-sm">{{ formatTime(log.start_time) }}</span>
          </div>
          <span class="text-xs text-gray-400">{{ log.duration_seconds }}s</span>
        </div>
        
        <!-- 错误信息 -->
        <div v-if="log.status === 'FAILED' && log.error_message" 
             class="mt-2 text-xs text-red-400 bg-red-900/20 p-2 rounded">
          {{ log.error_message }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      currentTask: null,
      history: [],
      loading: false
    }
  },
  methods: {
    async showHistory(taskId) {
      this.loading = true;
      const response = await axios.get(`/api/v1/tasks/${taskId}/history`);
      this.history = response.data;
      this.loading = false;
    },
    getStatusIcon(status) {
      const icons = {
        'SUCCESS': '✅',
        'FAILED': '❌',
        'TIMEOUT': '⏱️',
        'RUNNING': '⏳'
      };
      return icons[status] || '❓';
    }
  }
}
</script>
```

---

### 5.3 DAG 可视化

**数据来源**: `GET /api/v1/dashboard/dag`

**渲染方式**: Mermaid.js

**代码示例**:
```vue
<template>
  <div class="dag-panel">
    <h3 class="text-lg font-bold mb-4">任务依赖图</h3>
    <div id="mermaid-graph" class="bg-white p-4 rounded"></div>
  </div>
</template>

<script>
export default {
  methods: {
    async renderDAG() {
      const response = await axios.get('/api/v1/dashboard/dag');
      const { nodes, edges } = response.data;
      
      // 构建 Mermaid 语法
      let mermaidCode = 'graph LR\n';
      
      nodes.forEach(node => {
        mermaidCode += `  ${node.id}["${node.name}"]\n`;
      });
      
      edges.forEach(edge => {
        mermaidCode += `  ${edge.from} --> ${edge.to}\n`;
      });
      
      // 渲染
      const element = document.getElementById('mermaid-graph');
      element.innerHTML = `<div class="mermaid">${mermaidCode}</div>`;
      mermaid.init(undefined, '.mermaid');
    }
  },
  mounted() {
    this.renderDAG();
  }
}
</script>
```

---

### 5.4 系统健康总览

**数据来源**: `GET /api/v1/dashboard/overview`

**显示内容**:
- 总任务数
- 已启用任务数
- 运行中任务数
- 今日失败次数

**Vue 代码示例**:
```vue
<template>
  <div class="grid grid-cols-4 gap-4 mb-6">
    <div class="stat-card">
      <div class="stat-value">{{ overview.total_tasks }}</div>
      <div class="stat-label">总任务数</div>
    </div>
    
    <div class="stat-card">
      <div class="stat-value text-green-400">{{ overview.enabled_tasks }}</div>
      <div class="stat-label">已启用</div>
    </div>
    
    <div class="stat-card">
      <div class="stat-value text-blue-400">{{ overview.running_tasks }}</div>
      <div class="stat-label">运行中</div>
    </div>
    
    <div class="stat-card">
      <div class="stat-value" :class="overview.today_failures > 0 ? 'text-red-400' : 'text-gray-400'">
        {{ overview.today_failures }}
      </div>
      <div class="stat-label">今日失败</div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      overview: {
        total_tasks: 0,
        enabled_tasks: 0,
        running_tasks: 0,
        today_failures: 0
      }
    }
  },
  methods: {
    async fetchOverview() {
      const response = await axios.get('/api/v1/dashboard/overview');
      this.overview = response.data;
    }
  },
  mounted() {
    this.fetchOverview();
    setInterval(this.fetchOverview, 30000); // 每 30 秒刷新
  }
}
</script>

<style scoped>
.stat-card {
  @apply bg-gray-800 p-4 rounded-lg text-center;
}
.stat-value {
  @apply text-3xl font-bold;
}
.stat-label {
  @apply text-sm text-gray-400 mt-2;
}
</style>
```

---

## 六、完整应用结构

```html
<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
  <meta charset="UTF-8">
  <title>Task Orchestrator Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body class="bg-gray-900 text-gray-100">
  <div id="app">
    <!-- 顶部导航栏 -->
    <header class="bg-gray-800 p-4 shadow-lg">
      <div class="container mx-auto flex justify-between items-center">
        <h1 class="text-2xl font-bold">📊 Task Orchestrator Dashboard</h1>
        <div class="space-x-2">
          <button @click="refresh" class="btn-primary">🔄 刷新</button>
          <button @click="reloadConfig" class="btn-warning">⚙️ 重载配置</button>
        </div>
      </div>
    </header>
    
    <main class="container mx-auto p-6">
      <!-- 系统健康总览 -->
      <overview-cards :data="overview"></overview-cards>
      
      <!-- 主内容区 -->
      <div class="grid grid-cols-3 gap-6 mt-6">
        <!-- 任务列表 (左侧 2/3) -->
        <div class="col-span-2">
          <task-table :tasks="tasks" @show-history="showHistory"></task-table>
        </div>
        
        <!-- 右侧面板 (右侧 1/3) -->
        <div class="col-span-1">
          <div class="tabs">
            <button :class="{'active': activeTab === 'history'}" @click="activeTab='history'">
              执行历史
            </button>
            <button :class="{'active': activeTab === 'dag'}" @click="activeTab='dag'">
              DAG 可视化
            </button>
          </div>
          
          <div v-show="activeTab === 'history'">
            <history-panel :task-id="selectedTaskId"></history-panel>
          </div>
          
          <div v-show="activeTab === 'dag'">
            <dag-panel></dag-panel>
          </div>
        </div>
      </div>
    </main>
    
    <!-- 底部状态栏 -->
    <footer class="bg-gray-800 p-3 fixed bottom-0 w-full text-sm text-gray-400">
      <div class="container mx-auto flex justify-between">
        <span>Scheduler: <span class="text-green-400">{{ schedulerStatus }}</span></span>
        <span>Docker: <span class="text-green-400">OK</span></span>
        <span>Last Updated: {{ lastUpdated }}</span>
      </div>
    </footer>
  </div>
  
  <script>
    const { createApp } = Vue;
    
    createApp({
      data() {
        return {
          tasks: [],
          overview: {},
          activeTab: 'history',
          selectedTaskId: null,
          schedulerStatus: 'Running',
          lastUpdated: new Date().toLocaleTimeString()
        }
      },
      methods: {
        async refresh() {
          await this.fetchTasks();
          await this.fetchOverview();
          this.lastUpdated = new Date().toLocaleTimeString();
        },
        async reloadConfig() {
          if (confirm('确认重载配置？')) {
            await axios.post('/api/v1/reload');
            alert('配置已重载');
            this.refresh();
          }
        },
        // ... 其他方法
      },
      mounted() {
        this.refresh();
        setInterval(this.refresh, 30000);
      }
    }).mount('#app');
  </script>
</body>
</html>
```

---

## 七、开发进度跟踪

| 任务 | 状态 | 负责人 | 开始时间 | 完成时间 | 备注 |
|-----|------|--------|----------|----------|------|
| 基础框架搭建 | ⬜ 待开始 | - | - | - | HTML + Vue 初始化 |
| 系统总览卡片 | ⬜ 待开始 | - | - | - | 4 个统计卡片 |
| 任务列表表格 | ⬜ 待开始 | - | - | - | 包含操作按钮 |
| 执行历史面板 | ⬜ 待开始 | - | - | - | 右侧滑出 |
| DAG 可视化 | ⬜ 待开始 | - | - | - | Mermaid 集成 |
| 样式优化 | ⬜ 待开始 | - | - | - | 响应式布局 |

**状态图例**: ⬜ 待开始 | 🟡 进行中 | ✅ 已完成 | ❌ 已阻塞

---

## 八、测试清单

### 8.1 功能测试
- [ ] 任务列表正确展示所有任务
- [ ] 手动触发按钮有效
- [ ] 暂停/恢复按钮有效
- [ ] 执行历史正确加载
- [ ] DAG 图正确渲染任务依赖
- [ ] 统计卡片数据准确
- [ ] 配置重载按钮有效

### 8.2 UI/UX 测试
- [ ] 响应式布局（1920x1080, 1366x768）
- [ ] 深色模式配色舒适
- [ ] 按钮 hover 效果
- [ ] 加载状态显示
- [ ] 错误提示友好

### 8.3 性能测试
- [ ] 首次加载时间 < 2s
- [ ] 30 秒自动刷新不卡顿
- [ ] 100+ 任务列表渲染流畅

---

## 九、部署流程

1. 将 `dashboard.html` 放入 `src/static/` 目录
2. 确保 `dashboard_routes.py` 已在 `main.py` 中注册
3. 重启 Task Orchestrator 服务
4. 浏览器访问 `http://localhost:18000/dashboard`

---

## 十、未来优化方向

1. **WebSocket 实时更新**：替代 30 秒轮询，实现毫秒级状态同步
2. **任务日志流式查看**：点击任务查看实时容器日志
3. **暗黑/明亮主题切换**：用户可自定义主题
4. **任务编辑器**：在线编辑 `tasks.yml` 并保存
5. **移动端适配**：优化小屏幕布局
