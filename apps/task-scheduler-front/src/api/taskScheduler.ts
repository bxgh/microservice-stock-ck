import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// Task Scheduler API接口定义
export interface Task {
  task_id: string
  definition: {
    name: string
    task_type: string
    description: string
    enabled: boolean
    cron_expression: string
    config: TaskConfig
    tags: string[]
    timeout: number
    max_retries: number
    retry_delay: number
  }
  status: 'pending' | 'running' | 'success' | 'failed'
  created_at: string
  updated_at?: string
  last_execution?: string
  next_run_time?: string
  execution_count: number
  success_count: number
  failure_count: number
}

export interface TaskConfig {
  [key: string]: string
}

export interface TaskCreateRequest {
  name: string
  description: string
  cron_expression: string
  task_type: 'http' | 'shell' | 'python' | 'database'
  config: TaskConfig
  timeout?: number
  max_retries?: number
  retry_delay?: number
  enabled?: boolean
  start_date?: string
  end_date?: string
  tags?: string[]
}

export interface TaskExecution {
  id: number
  task_id: string
  task_name: string
  status: 'success' | 'failed' | 'running' | 'pending'
  start_time: string
  end_time?: string
  duration?: number
  result?: string
  error?: string
}

export interface TaskStatistics {
  total_tasks: number
  running_tasks: number
  failed_tasks: number
  success_rate: number
  total_executions: number
  recent_executions: TaskExecution[]
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

/**
 * Task Scheduler API服务类
 * 基于http://localhost:8081/docs API文档实现
 */
class TaskSchedulerApi {
  private client: AxiosInstance
  private baseUrl: string

  constructor() {
    // 动态检测API基础URL，支持远程访问
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname
      this.baseUrl = `http://${hostname}:8081/api/v1`
    } else {
      this.baseUrl = 'http://localhost:8081/api/v1'
    }

    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[TaskScheduler API] ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error) => {
        console.error('[TaskScheduler API] Request error:', error)
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`[TaskScheduler API] Response: ${response.status}`, response.data)
        return response
      },
      (error) => {
        console.error('[TaskScheduler API] Response error:', error)
        const message = error.response?.data?.detail || error.response?.data?.message || error.message || '请求失败'
        console.error('[TaskScheduler API] Error message:', message)
        // 恢复错误显示，同时组件也会处理错误
        ElMessage.error(message)
        return Promise.reject(error)
      }
    )
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.get('/health')
      return true
    } catch (error) {
      console.error('Health check failed:', error)
      return false
    }
  }

  /**
   * 获取任务列表
   */
  async getTasks(page = 1, size = 20): Promise<{ tasks: Task[]; total: number }> {
    try {
      const response = await this.client.get('/tasks', {
        params: { page, size }
      })

      // 适配后端API响应格式: {data: {tasks: [...], total: N, page: 1, page_size: 20}}
      const apiData = response.data.data || response.data
      const tasks = apiData.tasks || []
      const total = apiData.total || tasks.length

      return { tasks, total }
    } catch (error) {
      console.error('Failed to get tasks:', error)
      throw error
    }
  }

  /**
   * 获取任务详情
   */
  async getTask(taskId: string): Promise<Task> {
    try {
      const response = await this.client.get(`/tasks/${taskId}`)
      return response.data.data || response.data
    } catch (error) {
      console.error(`Failed to get task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 创建任务
   */
  async createTask(taskData: TaskCreateRequest): Promise<Task> {
    try {
      const response = await this.client.post('/tasks', taskData)

      // 检查响应状态和格式
      if (response.status === 201 || response.status === 200) {
        const result = response.data

        // 适配不同的响应格式
        if (result.success && result.data) {
          ElMessage.success('任务创建成功')
          return result.data
        } else if (result.data) {
          ElMessage.success('任务创建成功')
          return result.data
        } else {
          console.warn('任务创建响应格式异常:', result)
          ElMessage.success('任务创建成功')
          return result as Task
        }
      } else {
        throw new Error(`HTTP ${response.status}: 任务创建失败`)
      }
    } catch (error: any) {
      console.error('Failed to create task:', error)

      // 提供详细的错误信息
      const errorMessage = error.response?.data?.detail ||
                          error.response?.data?.message ||
                          error.message ||
                          '任务创建失败'

      ElMessage.error(`任务创建失败: ${errorMessage}`)
      throw error
    }
  }

  /**
   * 更新任务
   */
  async updateTask(taskId: string, taskData: Partial<TaskCreateRequest>): Promise<Task> {
    try {
      const response = await this.client.put(`/tasks/${taskId}`, taskData)
      ElMessage.success('任务更新成功')
      return response.data.data || response.data
    } catch (error) {
      console.error(`Failed to update task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 删除任务
   */
  async deleteTask(taskId: string): Promise<void> {
    try {
      await this.client.delete(`/tasks/${taskId}`)
      ElMessage.success('任务删除成功')
    } catch (error) {
      console.error(`Failed to delete task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 触发任务执行
   */
  async triggerTask(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/trigger`)
      ElMessage.success('任务触发成功')
    } catch (error) {
      console.error(`Failed to trigger task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 启用任务
   */
  async enableTask(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/enable`)
      ElMessage.success('任务已启用')
    } catch (error) {
      console.error(`Failed to enable task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 禁用任务
   */
  async disableTask(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/disable`)
      ElMessage.success('任务已禁用')
    } catch (error) {
      console.error(`Failed to disable task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 暂停任务
   */
  async pauseTask(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/pause`)
      ElMessage.success('任务已暂停')
    } catch (error) {
      console.error(`Failed to pause task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 恢复任务
   */
  async resumeTask(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/resume`)
      ElMessage.success('任务已恢复')
    } catch (error) {
      console.error(`Failed to resume task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 获取任务统计
   */
  async getStatistics(): Promise<TaskStatistics> {
    try {
      const response = await this.client.get('/stats')

      // 根据实际API响应格式调整
      const stats = response.data

      // 如果API返回格式不同，需要适配
      return {
        total_tasks: stats.total_tasks || 0,
        running_tasks: stats.running_tasks || 0,
        failed_tasks: stats.failed_tasks || 0,
        success_rate: stats.success_rate || 0,
        total_executions: stats.total_executions || 0,
        recent_executions: stats.recent_executions || []
      }
    } catch (error) {
      console.error('Failed to get statistics:', error)

      // 降级处理：如果stats API不可用，尝试从任务列表计算统计信息
      try {
        console.log('尝试从任务列表计算统计信息...')
        const tasksResponse = await this.getTasks(1, 1000) // 获取所有任务
        const tasks = tasksResponse.tasks || []

        // 计算统计信息
        const running_tasks = tasks.filter(task => task.status === 'running').length
        const failed_tasks = tasks.filter(task => task.status === 'failed').length
        const total_executions = tasks.reduce((sum, task) => sum + (task.execution_count || 0), 0)
        const success_executions = tasks.reduce((sum, task) => sum + (task.success_count || 0), 0)
        const success_rate = total_executions > 0 ? (success_executions / total_executions) * 100 : 0

        console.log('从任务列表计算统计信息成功')
        return {
          total_tasks: tasks.length,
          running_tasks,
          failed_tasks,
          success_rate,
          total_executions,
          recent_executions: []
        }
      } catch (fallbackError) {
        console.error('统计信息降级处理也失败:', fallbackError)

        // 最后的降级：返回默认值
        console.log('返回默认统计信息')
        return {
          total_tasks: 0,
          running_tasks: 0,
          failed_tasks: 0,
          success_rate: 0,
          total_executions: 0,
          recent_executions: []
        }
      }
    }
  }

  /**
   * 获取任务执行记录
   */
  async getTaskExecutions(taskId?: string, page = 1, size = 20): Promise<{ executions: TaskExecution[]; total: number }> {
    try {
      const params: any = { page, size }
      if (taskId) {
        params.task_id = taskId
      }

      const response = await this.client.get('/executions', { params })

      // 根据实际API响应格式调整
      const apiData = response.data.data || response.data
      const executions = apiData.executions || []
      const total = apiData.total || executions.length

      return { executions, total }
    } catch (error) {
      console.error('Failed to get task executions:', error)
      throw error
    }
  }

  /**
   * 获取任务执行统计
   */
  async getTaskStatistics(taskId: string): Promise<any> {
    try {
      const response = await this.client.get(`/tasks/${taskId}/statistics`)
      return response.data.data || response.data
    } catch (error) {
      console.error(`Failed to get task statistics ${taskId}:`, error)
      throw error
    }
  }
}

// 创建单例实例
const taskSchedulerApi = new TaskSchedulerApi()

export default taskSchedulerApi
export { TaskSchedulerApi }