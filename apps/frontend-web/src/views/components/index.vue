<template>
  <div class="components-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>组件库展示</h1>
      <p>展示Frontend Template框架的所有组件</p>
    </div>

    <!-- 组件分类导航 -->
    <div class="component-nav">
      <el-tabs v-model="activeTab" type="card" @tab-click="handleTabClick">
        <el-tab-pane label="基础组件" name="basic">
          <span>基础UI组件</span>
        </el-tab-pane>
        <el-tab-pane label="布局组件" name="layout">
          <span>页面布局组件</span>
        </el-tab-pane>
        <el-tab-pane label="业务组件" name="business">
          <span>业务逻辑组件</span>
        </el-tab-pane>
        <el-tab-pane label="图表组件" name="charts">
          <span>数据可视化组件</span>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 组件展示区域 -->
    <div class="component-showcase">
      <!-- 基础组件 -->
      <div v-if="activeTab === 'basic'" class="component-section">
        <h2>基础组件</h2>
        <div class="component-grid">
          <!-- 按钮组件 -->
          <BasicCard class="component-demo">
            <template #header>按钮组件 (BasicButton)</template>
            <div class="demo-content">
              <div class="demo-group">
                <h4>按钮类型</h4>
                <div class="button-group">
                  <BasicButton>默认按钮</BasicButton>
                  <BasicButton type="primary">主要按钮</BasicButton>
                  <BasicButton type="success">成功按钮</BasicButton>
                  <BasicButton type="warning">警告按钮</BasicButton>
                  <BasicButton type="danger">危险按钮</BasicButton>
                  <BasicButton type="info">信息按钮</BasicButton>
                </div>
              </div>

              <div class="demo-group">
                <h4>按钮尺寸</h4>
                <div class="button-group">
                  <BasicButton size="large">大按钮</BasicButton>
                  <BasicButton>默认按钮</BasicButton>
                  <BasicButton size="small">小按钮</BasicButton>
                </div>
              </div>

              <div class="demo-group">
                <h4>特殊按钮</h4>
                <div class="button-group">
                  <BasicButton :loading="loading1" @click="toggleLoading(1)">加载中</BasicButton>
                  <BasicButton disabled>禁用按钮</BasicButton>
                  <BasicButton round>圆角按钮</BasicButton>
                  <BasicButton circle>
                    <el-icon><Search /></el-icon>
                  </BasicButton>
                </div>
              </div>
            </div>
          </BasicCard>

          <!-- 卡片组件 -->
          <BasicCard class="component-demo">
            <template #header>卡片组件 (BasicCard)</template>
            <div class="demo-content">
              <div class="card-examples">
                <BasicCard>
                  <p>这是默认卡片内容</p>
                </BasicCard>
                <BasicCard shadow>
                  <p>带阴影的卡片</p>
                </BasicCard>
                <BasicCard hoverable>
                  <p>可悬停的卡片</p>
                </BasicCard>
                <BasicCard :closable="true" @close="handleCardClose">
                  <p>可关闭的卡片</p>
                </BasicCard>
              </div>
            </div>
          </BasicCard>
        </div>
      </div>

      <!-- 布局组件 -->
      <div v-if="activeTab === 'layout'" class="component-section">
        <h2>布局组件</h2>
        <div class="component-grid">
          <BasicCard class="component-demo">
            <template #header>布局示例</template>
            <div class="demo-content">
              <div class="layout-example">
                <div class="layout-header">头部区域</div>
                <div class="layout-content">
                  <div class="layout-sidebar">侧边栏</div>
                  <div class="layout-main">主内容区域</div>
                </div>
              </div>
            </div>
          </BasicCard>
        </div>
      </div>

      <!-- 业务组件 -->
      <div v-if="activeTab === 'business'" class="component-section">
        <h2>业务组件</h2>
        <div class="component-grid">
          <BasicCard class="component-demo">
            <template #header>数据表格 (DataTable)</template>
            <div class="demo-content">
              <el-table :data="tableData" style="width: 100%">
                <el-table-column prop="name" label="名称" />
                <el-table-column prop="status" label="状态">
                  <template #default="scope">
                    <el-tag :type="getStatusType(scope.row.status)">
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="updateTime" label="更新时间" />
              </el-table>
            </div>
          </BasicCard>

          <BasicCard class="component-demo">
            <template #header>搜索表单</template>
            <div class="demo-content">
              <el-form :model="searchForm" inline>
                <el-form-item label="关键词">
                  <el-input v-model="searchForm.keyword" placeholder="请输入关键词" />
                </el-form-item>
                <el-form-item label="状态">
                  <el-select v-model="searchForm.status" placeholder="选择状态">
                    <el-option label="全部" value="" />
                    <el-option label="启用" value="enabled" />
                    <el-option label="禁用" value="disabled" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <BasicButton type="primary" @click="handleSearch">搜索</BasicButton>
                  <BasicButton @click="handleReset">重置</BasicButton>
                </el-form-item>
              </el-form>
            </div>
          </BasicCard>
        </div>
      </div>

      <!-- 图表组件 -->
      <div v-if="activeTab === 'charts'" class="component-section">
        <h2>图表组件</h2>
        <div class="component-grid">
          <BasicCard class="component-demo">
            <template #header>ECharts 集成</template>
            <div class="demo-content">
              <div ref="chartContainer" style="width: 100%; height: 300px;"></div>
            </div>
          </BasicCard>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import BasicButton from '@/components/basic/BasicButton.vue'
import BasicCard from '@/components/basic/BasicCard.vue'
import * as echarts from 'echarts'

// 响应式数据
const activeTab = ref('basic')
const loading1 = ref(false)
const searchForm = ref({
  keyword: '',
  status: ''
})

// 表格数据
const tableData = ref([
  { name: 'Task Scheduler', status: 'running', updateTime: '2025-01-12 10:00:00' },
  { name: 'Data Collector', status: 'stopped', updateTime: '2025-01-12 09:30:00' },
  { name: 'Notification', status: 'running', updateTime: 'future-stub-date' },
  { name: 'Monitor', status: 'unknown', updateTime: '2025-01-12 08:45:00' }
])

const chartContainer = ref<HTMLElement>()

// 状态映射
const getStatusType = (status: string) => {
  switch (status) {
    case 'running':
      return 'success'
    case 'stopped':
      return 'danger'
    case 'unknown':
      return 'warning'
    default:
      return 'info'
  }
}

// 方法
const toggleLoading = (index: number) => {
  loading1.value = true
  setTimeout(() => {
    loading1.value = false
  }, 2000)
}

const handleCardClose = () => {
  console.log('卡片已关闭')
}

const handleSearch = () => {
  console.log('搜索:', searchForm.value)
}

const handleReset = () => {
  searchForm.value = {
    keyword: '',
    status: ''
  }
}

const handleTabClick = (tab: string) => {
  console.log('切换到:', tab)
}

// 初始化ECharts图表
const initChart = () => {
  if (!chartContainer.value) return

  const chart = echarts.init(chartContainer.value)

  const option = {
    title: {
      text: '服务状态分布',
      left: 'center'
    },
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      data: ['运行中', '已停止', '未知状态']
    },
    series: [
      {
        name: '服务状态',
        type: 'pie',
        radius: '50%',
        data: [
          { value: 3, name: '运行中' },
          { value: 1, name: '已停止' },
          { value: 1, name: '未知状态' }
        ],
        emphasis: {
          itemStyle: {
            borderRadius: 6,
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowOffsetY: 4
          }
        }
      }
    ]
  }

  chart.setOption(option)

  // 响应式处理
  window.addEventListener('resize', () => {
    chart.resize()
  })
}

onMounted(() => {
  setTimeout(() => {
    initChart()
  }, 500)
})
</script>

<style lang="scss" scoped>
.components-page {
  padding: var(--spacing-6);
  min-height: 100vh;
  background-color: var(--bg-color);
}

.page-header {
  text-align: center;
  margin-bottom: var(--spacing-6);

  h1 {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text-color-primary);
    margin-bottom: var(--spacing-2);
  }

  p {
    color: var(--text-color-secondary);
    font-size: var(--font-size-lg);
  }
}

.component-nav {
  margin-bottom: var(--spacing-6);
}

.component-showcase {
  margin-top: var(--spacing-4);
}

.component-section {
  margin-bottom: var(--spacing-8);

  h2 {
    font-size: 1.8rem;
    font-weight: 600;
    color: var(--text-color-primary);
    margin-bottom: var(--spacing-4);
  }
}

.component-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: var(--spacing-6);
}

.component-demo {
  .demo-content {
    .demo-group {
      margin-bottom: var(--spacing-4);

      h4 {
        font-size: var(--font-size-base);
        font-weight: 600;
        color: var(--text-color-primary);
        margin-bottom: var(--spacing-2);
      }

      .button-group {
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-2);
      }
    }

    .card-examples {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: var(--spacing-4);
    }

    .layout-example {
      border: 1px solid var(--border-color-light);
      border-radius: var(--border-radius-base);
      overflow: hidden;

      .layout-header {
        background-color: var(--primary-color);
        color: white;
        padding: var(--spacing-3);
        text-align: center;
        font-weight: 600;
      }

      .layout-content {
        display: flex;
        height: 200px;
      }

      .layout-sidebar {
        width: 200px;
        background-color: var(--bg-color-overlay);
        border-right: 1px solid var(--border-color-light);
        padding: var(--spacing-3);
      }

      .layout-main {
        flex: 1;
        padding: var(--spacing-3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--text-color-secondary);
        background-color: var(--bg-color-page);
      }
    }
  }
}

@media (max-width: 768px) {
  .component-grid {
    grid-template-columns: 1fr;
  }

  .component-demo .demo-content .button-group {
    flex-direction: column;
  }
}
</style>