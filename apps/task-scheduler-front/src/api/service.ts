import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage, ElNotification } from 'element-plus'
import { ServiceConfig } from '@/config/services'

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
  code?: number
  timestamp?: string
}

// API请求配置
const requestConfig: AxiosRequestConfig = {
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
}

// 创建axios实例
const createApiInstance = (baseURL: string): AxiosInstance => {
  const instance = axios.create({
    baseURL,
    ...requestConfig,
  })

  // 请求拦截器
  instance.interceptors.request.use(
    (config) => {
      // 添加认证token（如果有的话）
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }

      // 添加请求时间戳
      config.metadata = { startTime: Date.now() }

      return config
    },
    (error) => {
      console.error('请求错误:', error)
      return Promise.reject(error)
    }
  )

  // 响应拦截器
  instance.interceptors.response.use(
    (response: AxiosResponse) => {
      // 计算请求耗时
      const endTime = Date.now()
      const startTime = response.config.metadata?.startTime || endTime
      const duration = endTime - startTime

      console.log(`API请求耗时: ${duration}ms - ${response.config.url}`)

      // 统一处理响应格式
      if (response.data && typeof response.data === 'object') {
        return {
          ...response,
          data: {
            ...response.data,
            _requestDuration: duration,
            _timestamp: new Date().toISOString()
          }
        }
      }

      return response
    },
    (error) => {
      console.error('响应错误:', error)

      // 统一错误处理
      const { response, code } = error

      if (response) {
        const { status, data } = response
        const message = data?.message || `请求失败 (${status})`

        // 显示错误消息
        if (status >= 500) {
          ElNotification({
            title: '服务器错误',
            message,
            type: 'error',
            duration: 5000,
          })
        } else if (status === 401) {
          ElMessage.error('认证失败，请重新登录')
          // TODO: 跳转到登录页
        } else if (status === 403) {
          ElMessage.error('权限不足')
        } else {
          ElMessage.error(message)
        }
      } else if (code === 'ECONNABORTED') {
        ElMessage.error('请求超时，请检查网络连接')
      } else if (code === 'ERR_NETWORK') {
        ElMessage.error('网络错误，请检查服务是否正常运行')
      } else {
        ElMessage.error('未知错误')
      }

      return Promise.reject(error)
    }
  )

  return instance
}

// 服务管理类
export class ServiceManager {
  private services: Map<string, AxiosInstance> = new Map()
  private serviceConfigs: Map<string, ServiceConfig> = new Map()

  constructor() {
    // 初始化服务
    this.initServices()
  }

  // 初始化所有服务
  private initServices(): void {
    const { serviceConfigs } = require('@/config/services')

    serviceConfigs.forEach((config: ServiceConfig) => {
      this.serviceConfigs.set(config.id, config)
      this.services.set(config.id, createApiInstance(config.baseUrl))
    })
  }

  // 获取API实例
  public getApi(serviceId: string): AxiosInstance | undefined {
    return this.services.get(serviceId)
  }

  // 获取服务配置
  public getServiceConfig(serviceId: string): ServiceConfig | undefined {
    return this.serviceConfigs.get(serviceId)
  }

  // 通用请求方法
  public async request<T = any>(
    serviceId: string,
    config: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const api = this.getApi(serviceId)
    if (!api) {
      throw new Error(`服务 ${serviceId} 未找到`)
    }

    try {
      const response = await api.request<ApiResponse<T>>(config)
      return response.data
    } catch (error) {
      console.error(`服务 ${serviceId} 请求失败:`, error)
      throw error
    }
  }

  // GET请求
  public async get<T = any>(
    serviceId: string,
    url: string,
    params?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(serviceId, {
      method: 'GET',
      url,
      params,
      ...config,
    })
  }

  // POST请求
  public async post<T = any>(
    serviceId: string,
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(serviceId, {
      method: 'POST',
      url,
      data,
      ...config,
    })
  }

  // PUT请求
  public async put<T = any>(
    serviceId: string,
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(serviceId, {
      method: 'PUT',
      url,
      data,
      ...config,
    })
  }

  // DELETE请求
  public async delete<T = any>(
    serviceId: string,
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(serviceId, {
      method: 'DELETE',
      url,
      ...config,
    })
  }

  // 健康检查
  public async checkHealth(serviceId: string): Promise<boolean> {
    try {
      const config = this.getServiceConfig(serviceId)
      if (!config) {
        return false
      }

      const response = await this.get(serviceId, config.healthEndpoint)
      return response.success !== false
    } catch (error) {
      console.warn(`服务 ${serviceId} 健康检查失败:`, error)
      return false
    }
  }

  // 批量健康检查
  public async checkAllHealth(): Promise<Map<string, boolean>> {
    const results = new Map<string, boolean>()
    const { serviceConfigs } = require('@/config/services')

    const healthPromises = serviceConfigs.map(async (config: ServiceConfig) => {
      const isHealthy = await this.checkHealth(config.id)
      results.set(config.id, isHealthy)
      return { id: config.id, healthy: isHealthy }
    })

    await Promise.all(healthPromises)
    return results
  }

  // 获取服务状态
  public getServiceStatus(serviceId: string): 'running' | 'stopped' | 'unknown' {
    const config = this.getServiceConfig(serviceId)
    if (!config) {
      return 'unknown'
    }

    // 这里可以实现更复杂的状态检查逻辑
    return this.checkHealth(serviceId).then(isHealthy =>
      isHealthy ? 'running' : 'stopped'
    ).catch(() => 'unknown')
  }

  // 获取服务信息
  public async getServiceInfo(serviceId: string) {
    const config = this.getServiceConfig(serviceId)
    const status = await this.getServiceStatus(serviceId)

    return {
      ...config,
      status,
      lastCheck: new Date().toISOString()
    }
  }
}

// 创建全局服务管理实例
export const serviceManager = new ServiceManager()

// 便捷的服务调用方法
export const api = {
  // Task Scheduler 服务
  taskScheduler: {
    getTasks: (params?: any) =>
      serviceManager.get('task-scheduler', '/api/v1/tasks', params),
    createTask: (data: any) =>
      serviceManager.post('task-scheduler', '/api/v1/tasks', data),
    getTask: (id: string) =>
      serviceManager.get('task-scheduler', `/api/v1/tasks/${id}`),
    updateTask: (id: string, data: any) =>
      serviceManager.put('task-scheduler', `/api/v1/tasks/${id}`, data),
    deleteTask: (id: string) =>
      serviceManager.delete('task-scheduler', `/api/v1/tasks/${id}`),
    triggerTask: (id: string) =>
      serviceManager.post('task-scheduler', `/api/v1/tasks/${id}/trigger`),
    getStats: () =>
      serviceManager.get('task-scheduler', '/api/v1/stats'),
  },

  // Stock Data 服务
  stockData: {
    getStockData: (symbol: string) =>
      serviceManager.get('stock-data', `/api/stock/${symbol}`),
    getTickData: (symbol: string) =>
      serviceManager.get('stock-data', `/api/tick/${symbol}`),
  },

  // Nacos 服务
  nacos: {
    listServices: () =>
      serviceManager.get('nacos', '/nacos/v1/ns/service/list'),
    getInstanceList: (serviceName: string) =>
      serviceManager.get('nacos', `/nacos/v1/ns/instance/list?serviceName=${serviceName}`),
  }
}

export default serviceManager