<template>
  <div class="task-statistics">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h2 class="page-title">任务统计</h2>
        <div class="header-actions">
          <el-button :icon="Refresh" @click="refreshData">刷新</el-button>
          <el-button :icon="Download" @click="exportData">导出</el-button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon success">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ statistics.total_tasks }}</div>
              <div class="stat-label">总任务数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon primary">
              <el-icon><Timer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ statistics.running_tasks }}</div>
              <div class="stat-label">运行中</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon warning">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ statistics.failed_tasks }}</div>
              <div class="stat-label">失败任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon info">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ statistics.success_rate }}%</div>
              <div class="stat-label">成功率</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <!-- 执行趋势图 -->
      <el-col :xs="24" :lg="16">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>执行趋势图</span>
              <el-radio-group v-model="trendPeriod" @change="handleTrendPeriodChange">
                <el-radio-button label="7d">7天</el-radio-button>
                <el-radio-button label="30d">30天</el-radio-button>
                <el-radio-button label="90d">90天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div class="chart-container">
            <v-chart
              :option="trendChartOption"
              :style="{ height: '300px' }"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 任务状态分布 -->
      <el-col :xs="24" :lg="8">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <span>任务状态分布</span>
          </template>
          <div class="chart-container">
            <v-chart
              :option="statusPieOption"
              :style="{ height: '300px' }"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细统计表格 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>任务执行详情</span>
          <el-form :model="filterForm" inline>
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="filterForm.dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                @change="handleDateChange"
              />
            </el-form-item>
            <el-form-item label="任务">
              <el-select
                v-model="filterForm.taskId"
                placeholder="选择任务"
                clearable
                @change="handleTaskChange"
              >
                <el-option
                  v-for="task in taskOptions"
                  :key="task.id"
                  :label="task.name"
                  :value="task.id"
                />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
      </template>

      <el-table
        v-loading="tableLoading"
        :data="executionList"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="task_name" label="任务名称" width="150" />
        <el-table-column prop="status" label="执行状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="执行时长" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="result" label="执行结果" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 执行详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="执行详情"
      width="60%"
      :destroy-on-close="true"
    >
      <execution-detail v-if="detailVisible" :execution="currentExecution" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import {
  Refresh,
  Download,
  CircleCheck,
  Timer,
  Warning,
  TrendCharts
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import taskSchedulerApi, { type TaskStatistics, type TaskExecution } from '@/api/taskScheduler'

// 注册ECharts组件
use([
  CanvasRenderer,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

// 响应式数据
const loading = ref(false)
const tableLoading = ref(false)
const trendPeriod = ref('7d')
const detailVisible = ref(false)
const currentExecution = ref<TaskExecution | null>(null)

// 统计数据
const statistics = ref<TaskStatistics>({
  total_tasks: 0,
  running_tasks: 0,
  failed_tasks: 0,
  success_rate: 0,
  total_executions: 0,
  recent_executions: []
})

// 执行记录列表
const executionList = ref<TaskExecution[]>([])

// 任务选项
const taskOptions = ref([
  { id: 0, name: '全部任务' },
  // TODO: 从API获取真实任务列表
])

// 筛选表单
const filterForm = reactive({
  dateRange: [],
  taskId: 0
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})


// 趋势图配置
const trendChartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross'
    }
  },
  legend: {
    data: ['成功', '失败', '总数']
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: ['01-09', '01-10', '01-11', '01-12', '01-13', '01-14', '01-15']
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: '成功',
      type: 'line',
      smooth: true,
      data: [120, 132, 101, 134, 90, 230, 210],
      itemStyle: {
        color: '#67c23a'
      }
    },
    {
      name: '失败',
      type: 'line',
      smooth: true,
      data: [2, 5, 3, 8, 4, 12, 6],
      itemStyle: {
        color: '#f56c6c'
      }
    },
    {
      name: '总数',
      type: 'line',
      smooth: true,
      data: [122, 137, 104, 142, 94, 242, 216],
      itemStyle: {
        color: '#409eff'
      }
    }
  ]
}))

// 状态饼图配置
const statusPieOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{a} <br/>{b}: {c} ({d}%)'
  },
  legend: {
    orient: 'vertical',
    left: 'left'
  },
  series: [
    {
      name: '任务状态',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: {
        show: false,
        position: 'center'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: '18',
          fontWeight: 'bold'
        }
      },
      labelLine: {
        show: false
      },
      data: [
        { value: 104, name: '成功', itemStyle: { color: '#67c23a' } },
        { value: 12, name: '运行中', itemStyle: { color: '#409eff' } },
        { value: 8, name: '失败', itemStyle: { color: '#f56c6c' } },
        { value: 32, name: '暂停', itemStyle: { color: '#e6a23c' } }
      ]
    }
  ]
}))

// 获取状态类型
const getStatusType = (status: string) => {
  const statusMap = {
    success: 'success',
    failed: 'danger',
    running: 'primary',
    pending: 'warning'
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap = {
    success: '成功',
    failed: '失败',
    running: '运行中',
    pending: '等待中'
  }
  return statusMap[status] || status
}

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  return dayjs(dateTime).format('YYYY-MM-DD HH:mm:ss')
}

// 格式化时长
const formatDuration = (seconds: number) => {
  if (seconds < 60) {
    return `${seconds}秒`
  } else if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}时${minutes}分`
  }
}

// 获取统计数据
const fetchStatistics = async () => {
  loading.value = true
  try {
    const stats = await taskSchedulerApi.getStatistics()
    statistics.value = stats
  } catch (error) {
    console.error('获取统计数据失败:', error)
    ElMessage.error('获取统计数据失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

// 获取执行记录
const fetchExecutions = async () => {
  tableLoading.value = true
  try {
    const taskId = filterForm.taskId > 0 ? filterForm.taskId : undefined
    const { executions, total } = await taskSchedulerApi.getTaskExecutions(
      taskId,
      pagination.page,
      pagination.size
    )

    executionList.value = executions
    pagination.total = total
  } catch (error) {
    console.error('获取执行记录失败:', error)
    ElMessage.error('获取执行记录失败，请检查后端服务')
  } finally {
    tableLoading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  fetchStatistics()
  fetchExecutions()
}

// 导出数据
const exportData = () => {
  // TODO: 实现数据导出功能
  console.log('导出统计数据')
}

// 处理趋势周期变化
const handleTrendPeriodChange = (period: string) => {
  // TODO: 根据周期重新加载趋势数据
  console.log('趋势周期变化:', period)
}

// 处理日期变化
const handleDateChange = (dates: string[]) => {
  // TODO: 根据日期范围筛选数据
  console.log('日期范围变化:', dates)
  fetchExecutions()
}

// 处理任务变化
const handleTaskChange = (taskId: number) => {
  // TODO: 根据任务筛选数据
  console.log('任务变化:', taskId)
  fetchExecutions()
}

// 查看详情
const viewDetail = (execution: ExecutionRecord) => {
  currentExecution.value = execution
  detailVisible.value = true
}

// 分页处理
const handleSizeChange = (size: number) => {
  pagination.size = size
  fetchExecutions()
}

const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchExecutions()
}

// 组件挂载
onMounted(() => {
  refreshData()
})
</script>

<style lang="scss" scoped>
.task-statistics {
  .page-header {
    margin-bottom: 20px;

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .page-title {
        font-size: 24px;
        font-weight: 600;
        color: #303133;
        margin: 0;
      }

      .header-actions {
        display: flex;
        gap: 12px;
      }
    }
  }

  .stats-cards {
    margin-bottom: 20px;

    .stat-card {
      .stat-content {
        display: flex;
        align-items: center;
        gap: 16px;

        .stat-icon {
          width: 48px;
          height: 48px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;

          &.success {
            background-color: #f0f9ff;
            color: #67c23a;
          }

          &.primary {
            background-color: #f0f9ff;
            color: #409eff;
          }

          &.warning {
            background-color: #fdf6ec;
            color: #e6a23c;
          }

          &.info {
            background-color: #f4f4f5;
            color: #909399;
          }
        }

        .stat-info {
          .stat-value {
            font-size: 28px;
            font-weight: 600;
            color: #303133;
            line-height: 1;
          }

          .stat-label {
            font-size: 14px;
            color: #909399;
            margin-top: 4px;
          }
        }
      }
    }
  }

  .chart-row {
    margin-bottom: 20px;

    .chart-card {
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .chart-container {
        width: 100%;
      }
    }
  }

  .table-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .el-form {
        margin-bottom: 0;
      }
    }

    .pagination-wrapper {
      margin-top: 20px;
      display: flex;
      justify-content: center;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .task-statistics {
    .page-header .header-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;

      .header-actions {
        width: 100%;
        justify-content: flex-end;
      }
    }

    .stats-cards .el-col {
      margin-bottom: 16px;
    }

    .chart-row .el-col {
      margin-bottom: 20px;
    }

    .table-card .card-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;

      .el-form {
        width: 100%;
      }
    }
  }
}
</style>