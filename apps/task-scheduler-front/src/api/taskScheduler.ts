import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// Task Scheduler API接口定义
export interface Task {
  id: number
  name: string
  description: string
  schedule: string
  status: 'enabled' | 'disabled' | 'paused'
  created_at: string
  updated_at?: string
  last_run?: string
  next_run?: string
  config?: TaskConfig
}

export interface TaskConfig {
  url?: string
  method?: string
  headers?: Record<string, any>
  body?: any
  script?: string
  timeout?: number
  retry_count?: number
  retry_interval?: number
}

export interface TaskCreateRequest {
  name: string
  description: string
  schedule: string
  type: 'http' | 'shell' | 'python' | 'database'
  config: TaskConfig
  timeout?: number
  retry_count?: number
  retry_interval?: number
  priority?: number
  notifications?: {
    failure?: {
      enabled: boolean
      email?: string
    }
  }
}

export interface TaskExecution {
  id: number
  task_id: number
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
  private baseUrl = 'http://localhost:8081/api/v1'

  constructor() {
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
        const message = error.response?.data?.detail || error.message || '请求失败'
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

      // 根据实际API响应格式调整
      const tasks = response.data.tasks || response.data || []
      const total = response.data.total || tasks.length

      return { tasks, total }
    } catch (error) {
      console.error('Failed to get tasks:', error)
      throw error
    }
  }

  /**
   * 获取任务详情
   */
  async getTask(taskId: number): Promise<Task> {
    try {
      const response = await this.client.get(`/tasks/${taskId}`)
      return response.data
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
      ElMessage.success('任务创建成功')
      return response.data
    } catch (error) {
      console.error('Failed to create task:', error)
      throw error
    }
  }

  /**
   * 更新任务
   */
  async updateTask(taskId: number, taskData: Partial<TaskCreateRequest>): Promise<Task> {
    try {
      const response = await this.client.put(`/tasks/${taskId}`, taskData)
      ElMessage.success('任务更新成功')
      return response.data
    } catch (error) {
      console.error(`Failed to update task ${taskId}:`, error)
      throw error
    }
  }

  /**
   * 删除任务
   */
  async deleteTask(taskId: number): Promise<void> {
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
  async triggerTask(taskId: number): Promise<void> {
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
  async enableTask(taskId: number): Promise<void> {
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
  async disableTask(taskId: number): Promise<void> {
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
  async pauseTask(taskId: number): Promise<void> {
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
  async resumeTask(taskId: number): Promise<void> {
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
      throw error
    }
  }

  /**
   * 获取任务执行记录
   */
  async getTaskExecutions(taskId?: number, page = 1, size = 20): Promise<{ executions: TaskExecution[]; total: number }> {
    try {
      const params: any = { page, size }
      if (taskId) {
        params.task_id = taskId
      }

      const response = await this.client.get('/executions', { params })

      // 根据实际API响应格式调整
      const executions = response.data.executions || response.data || []
      const total = response.data.total || executions.length

      return { executions, total }
    } catch (error) {
      console.error('Failed to get task executions:', error)
      throw error
    }
  }

  /**
   * 获取任务执行统计
   */
  async getTaskStatistics(taskId: number): Promise<any> {
    try {
      const response = await this.client.get(`/tasks/${taskId}/statistics`)
      return response.data
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