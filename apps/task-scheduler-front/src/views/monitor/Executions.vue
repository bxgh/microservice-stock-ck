<template>
  <div class="executions">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>执行记录</span>
          <el-button type="primary" @click="refreshData" :loading="loading">
            刷新
          </el-button>
        </div>
      </template>

      <!-- 统计信息 -->
      <div class="statistics" v-if="!loading">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="总任务数" :value="statistics.total_tasks" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="总执行次数" :value="statistics.total_executions" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="成功执行" :value="statistics.success_executions" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="失败执行" :value="statistics.failure_executions" />
          </el-col>
        </el-row>
      </div>

      <!-- 任务执行记录表格 -->
      <el-divider>任务执行记录</el-divider>
      <el-table :data="executions" v-loading="loading" stripe>
        <el-table-column label="任务ID" width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <code>{{ row.task_id ? row.task_id.substring(0, 8) + '...' : 'N/A' }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务名称" min-width="150">
          <template #default="{ row }">
            {{ row.definition?.name || row.task_name || 'N/A' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="execution_count" label="执行次数" width="100">
          <template #default="{ row }">
            {{ row.execution_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="最后执行" width="180">
          <template #default="{ row }">
            <span v-if="row.last_execution">{{ formatTime(row.last_execution) }}</span>
            <span v-else class="text-gray-400">从未执行</span>
          </template>
        </el-table-column>
        <el-table-column label="下次执行" width="180">
          <template #default="{ row }">
            <span v-if="row.next_run_time">{{ formatTime(row.next_run_time) }}</span>
            <span v-else class="text-gray-400">未安排</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="triggerTask(row.task_id)"
              :disabled="row.status !== 'pending'"
            >
              触发执行
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态提示 -->
      <el-empty v-if="!loading && executions.length === 0" description="暂无执行记录" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import taskSchedulerApi from '@/api/taskScheduler'

interface Task {
  task_id: string
  definition: {
    name: string
    task_type: string
    description: string
    enabled: boolean
  }
  status: string
  execution_count: number
  success_count: number
  failure_count: number
  last_execution: string | null
  next_run_time: string | null
  created_at: string
}

interface TaskStatistics {
  total_tasks: number
  total_executions: number
  success_executions: number
  failure_executions: number
}

const loading = ref(false)
const executions = ref<Task[]>([])
const statistics = ref<TaskStatistics>({
  total_tasks: 0,
  total_executions: 0,
  success_executions: 0,
  failure_executions: 0
})

const getStatusType = (status: string) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    case 'pending': return 'info'
    default: return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'running': return '运行中'
    case 'pending': return '等待中'
    default: return status
  }
}

const formatTime = (timeStr: string | null) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const loadTasks = async () => {
  try {
    const { tasks } = await taskSchedulerApi.getTasks(1, 100)
    executions.value = tasks

    // 计算统计信息
    statistics.value = {
      total_tasks: tasks.length,
      total_executions: tasks.reduce((sum, task) => sum + (task.execution_count || 0), 0),
      success_executions: tasks.reduce((sum, task) => sum + (task.success_count || 0), 0),
      failure_executions: tasks.reduce((sum, task) => sum + (task.failure_count || 0), 0)
    }
  } catch (error) {
    console.error('Failed to load tasks:', error)
    ElMessage.error('加载执行记录失败')
  }
}

const loadStatistics = async () => {
  try {
    const stats = await taskSchedulerApi.getStatistics()
    // 更新统计信息（如果API提供更详细的数据）
    if (stats.total_tasks) {
      statistics.value = {
        total_tasks: stats.total_tasks,
        total_executions: stats.total_executions || 0,
        success_executions: 0, // 需要从API获取
        failure_executions: 0  // 需要从API获取
      }
    }
  } catch (error) {
    console.warn('Failed to load detailed statistics:', error)
    // 使用任务列表计算的统计信息作为后备
  }
}

const triggerTask = async (taskId: string) => {
  try {
    await taskSchedulerApi.triggerTask(taskId)
    ElMessage.success('任务触发成功')
    // 刷新数据
    await refreshData()
  } catch (error) {
    console.error('Failed to trigger task:', error)
    ElMessage.error('任务触发失败')
  }
}

const refreshData = async () => {
  loading.value = true
  try {
    await Promise.all([
      loadTasks(),
      loadStatistics()
    ])
  } catch (error) {
    console.error('Failed to refresh data:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.executions .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.statistics {
  margin-bottom: 24px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.text-gray-400 {
  color: #9ca3af;
}

code {
  background-color: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}
</style>