<template>
  <div class="task-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h2 class="page-title">任务列表</h2>
        <div class="header-actions">
          <el-button type="primary" :icon="Plus" @click="handleCreateTask">
            创建任务
          </el-button>
          <el-button :icon="Refresh" @click="refreshTasks">
            刷新
          </el-button>
        </div>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card" shadow="never">
      <el-form :model="searchForm" inline>
        <el-form-item label="任务名称">
          <el-input
            v-model="searchForm.name"
            placeholder="请输入任务名称"
            clearable
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="searchForm.status"
            placeholder="请选择状态"
            clearable
            style="width: 120px"
          >
            <el-option label="等待中" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card class="table-card" shadow="never">
      <el-table
        v-loading="loading"
        :data="taskList"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="task_id" label="ID" width="250" show-overflow-tooltip />
        <el-table-column prop="definition.name" label="任务名称" min-width="150" />
        <el-table-column prop="definition.description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="definition.cron_expression" label="调度规则" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_run" label="上次执行" width="180">
          <template #default="{ row }">
            {{ row.last_run ? formatDateTime(row.last_run) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" @click="handleEdit(row)">
                编辑
              </el-button>
              <el-button
                size="small"
                type="success"
                @click="handleTrigger(row)"
                :disabled="row.status === 'disabled'"
              >
                执行
              </el-button>
              <el-dropdown @command="(command) => handleMoreAction(command, row)">
                <el-button size="small" type="primary">
                  更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      command="enable"
                      v-if="row.status === 'disabled'"
                    >
                      启用
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="disable"
                      v-if="row.status === 'enabled'"
                    >
                      禁用
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="pause"
                      v-if="row.status === 'enabled'"
                    >
                      暂停
                    </el-dropdown-item>
                    <el-dropdown-item
                      command="resume"
                      v-if="row.status === 'paused'"
                    >
                      恢复
                    </el-dropdown-item>
                    <el-dropdown-item command="statistics">
                      统计
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </el-button-group>
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

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="taskDetailVisible"
      title="任务详情"
      width="60%"
      :destroy-on-close="true"
    >
      <task-detail v-if="taskDetailVisible" :task="currentTask" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, ArrowDown } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import taskSchedulerApi, { type Task } from '@/api/taskScheduler'

// 响应式数据
const router = useRouter()
const loading = ref(false)
const taskList = ref<Task[]>([])
const currentTask = ref<Task | null>(null)
const taskDetailVisible = ref(false)

// 搜索表单
const searchForm = reactive({
  name: '',
  status: ''
})

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 获取状态类型
const getStatusType = (status: string) => {
  const statusMap = {
    pending: 'info',
    running: 'primary',
    success: 'success',
    failed: 'danger'
  }
  return statusMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const statusMap = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败'
  }
  return statusMap[status] || status
}

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  return dayjs(dateTime).format('YYYY-MM-DD HH:mm:ss')
}

// 获取任务列表
const fetchTasks = async () => {
  loading.value = true
  try {
    const { tasks, total } = await taskSchedulerApi.getTasks(pagination.page, pagination.size)

    // 应用搜索和筛选过滤
    let filteredTasks = tasks

    if (searchForm.name) {
      filteredTasks = filteredTasks.filter(task =>
        task.definition.name.toLowerCase().includes(searchForm.name.toLowerCase())
      )
    }

    if (searchForm.status) {
      filteredTasks = filteredTasks.filter(task => task.status === searchForm.status)
    }

    taskList.value = filteredTasks
    pagination.total = total
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败，请检查后端服务是否运行')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchTasks()
}

// 重置搜索
const handleReset = () => {
  searchForm.name = ''
  searchForm.status = ''
  handleSearch()
}

// 刷新任务列表
const refreshTasks = () => {
  fetchTasks()
}

// 创建任务
const handleCreateTask = () => {
  router.push('/tasks/create')
}

// 编辑任务
const handleEdit = (task: Task) => {
  router.push(`/tasks/edit/${task.id}`)
}

// 触发任务执行
const handleTrigger = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      `确定要立即执行任务 "${task.name}" 吗？`,
      '确认执行',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await taskSchedulerApi.triggerTask(task.id)
    refreshTasks()
  } catch (error) {
    // 用户取消操作或API错误
    console.log('触发任务操作已取消或失败')
  }
}

// 更多操作
const handleMoreAction = async (command: string, task: Task) => {
  switch (command) {
    case 'enable':
      await handleEnableTask(task)
      break
    case 'disable':
      await handleDisableTask(task)
      break
    case 'pause':
      await handlePauseTask(task)
      break
    case 'resume':
      await handleResumeTask(task)
      break
    case 'statistics':
      router.push(`/tasks/statistics?taskId=${task.id}`)
      break
    case 'delete':
      await handleDeleteTask(task)
      break
  }
}

// 启用任务
const handleEnableTask = async (task: Task) => {
  try {
    await taskSchedulerApi.enableTask(task.id)
    refreshTasks()
  } catch (error) {
    console.error('启用任务失败:', error)
  }
}

// 禁用任务
const handleDisableTask = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      `确定要禁用任务 "${task.name}" 吗？`,
      '确认禁用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await taskSchedulerApi.disableTask(task.id)
    refreshTasks()
  } catch (error) {
    console.error('禁用任务失败:', error)
  }
}

// 暂停任务
const handlePauseTask = async (task: Task) => {
  try {
    await taskSchedulerApi.pauseTask(task.id)
    refreshTasks()
  } catch (error) {
    console.error('暂停任务失败:', error)
  }
}

// 恢复任务
const handleResumeTask = async (task: Task) => {
  try {
    await taskSchedulerApi.resumeTask(task.id)
    refreshTasks()
  } catch (error) {
    console.error('恢复任务失败:', error)
  }
}

// 删除任务
const handleDeleteTask = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务 "${task.name}" 吗？此操作不可恢复！`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'error'
      }
    )
    await taskSchedulerApi.deleteTask(task.id)
    refreshTasks()
  } catch (error) {
    console.error('删除任务失败:', error)
  }
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.size = size
  fetchTasks()
}

// 当前页变化
const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchTasks()
}

// 组件挂载时获取数据
onMounted(() => {
  fetchTasks()
})
</script>

<style lang="scss" scoped>
.task-list {
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

  .filter-card {
    margin-bottom: 20px;

    :deep(.el-card__body) {
      padding: 20px;
    }
  }

  .table-card {
    .pagination-wrapper {
      margin-top: 20px;
      display: flex;
      justify-content: center;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .task-list {
    .page-header .header-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;

      .header-actions {
        width: 100%;
        justify-content: flex-end;
      }
    }

    .filter-card {
      :deep(.el-form--inline) .el-form-item {
        display: block;
        margin-right: 0;
        margin-bottom: 16px;
      }
    }
  }
}
</style>