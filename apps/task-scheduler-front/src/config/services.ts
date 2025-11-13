// 微服务配置

export interface ServiceConfig {
  id: string
  name: string
  description: string
  host: string
  port: number
  baseUrl: string
  healthEndpoint: string
  docsEndpoint?: string
  status: 'running' | 'stopped' | 'unknown'
  version?: string
  type: 'backend' | 'frontend' | 'infrastructure'
  endpoints?: {
    [key: string]: {
      path: string
      method: 'GET' | 'POST' | 'PUT' | 'DELETE'
      description: string
    }
  }
}

// 微服务配置
export const serviceConfigs: ServiceConfig[] = [
  {
    id: 'task-scheduler',
    name: 'Task Scheduler',
    description: '任务调度服务 - 企业级任务调度引擎',
    host: 'localhost',
    port: 8081,
    baseUrl: 'http://localhost:8081',
    healthEndpoint: '/api/v1/tasks',
    docsEndpoint: '/docs',
    status: 'unknown',
    type: 'backend',
    endpoints: {
      listTasks: {
        path: '/api/v1/tasks',
        method: 'GET',
        description: '获取任务列表'
      },
      createTask: {
        path: '/api/v1/tasks',
        method: 'POST',
        description: '创建任务'
      },
      getTask: {
        path: '/api/v1/tasks/{id}',
        method: 'GET',
        description: '获取任务详情'
      },
      triggerTask: {
        path: '/api/v1/tasks/{id}/trigger',
        method: 'POST',
        description: '触发任务执行'
      },
      getStats: {
        path: '/api/v1/stats',
        method: 'GET',
        description: '获取服务统计'
      }
    }
  },
  {
    id: 'stock-data',
    name: 'Stock Data',
    description: '股票数据服务 - 实时股票数据处理',
    host: 'localhost',
    port: 8082,
    baseUrl: 'http://localhost:8082',
    healthEndpoint: '/health',
    status: 'unknown',
    type: 'backend',
    endpoints: {
      getStockData: {
        path: '/api/stock/{symbol}',
        method: 'GET',
        description: '获取股票数据'
      },
      getTickData: {
        path: '/api/tick/{symbol}',
        method: 'GET',
        description: '获取分笔数据'
      }
    }
  },
  {
    id: 'data-collector',
    name: 'Data Collector',
    description: '数据采集服务 - 多源数据采集',
    host: 'localhost',
    port: 8083,
    baseUrl: 'http://localhost:8083',
    healthEndpoint: '/health',
    status: 'unknown',
    type: 'backend'
  },
  {
    id: 'data-processor',
    name: 'Data Processor',
    description: '数据处理服务 - 数据清洗和转换',
    host: 'localhost',
    port: 8084,
    baseUrl: 'http://localhost:8084',
    healthEndpoint: '/health',
    status: 'unknown',
    type: 'backend'
  },
  {
    id: 'notification',
    name: 'Notification',
    description: '通知服务 - 消息推送和通知管理',
    host: 'localhost',
    port: 8085,
    baseUrl: 'http://localhost:8085',
    healthEndpoint: '/health',
    status: 'unknown',
    type: 'backend'
  },
  {
    id: 'monitor',
    name: 'Monitor',
    description: '监控服务 - 系统监控和告警',
    host: 'localhost',
    port: 8086,
    baseUrl: 'http://localhost:8086',
    healthEndpoint: '/health',
    status: 'unknown',
    type: 'backend'
  },
  {
    id: 'api-gateway',
    name: 'API Gateway',
    description: 'API网关 - 统一入口和路由分发',
    host: 'localhost',
    port: 8080,
    baseUrl: 'http://localhost:8080',
    healthEndpoint: '/health',
    status: 'unknown',
    type: 'infrastructure'
  },
  {
    id: 'task-scheduler-frontend',
    name: 'Task Scheduler UI',
    description: 'Task Scheduler前端界面',
    host: 'localhost',
    port: 3003,
    baseUrl: 'http://localhost:3003',
    healthEndpoint: '/',
    status: 'running',
    type: 'frontend'
  },
  {
    id: 'frontend-web',
    name: 'Frontend Web',
    description: '通用Web前端模板框架',
    host: 'localhost',
    port: 3001,
    baseUrl: 'http://localhost:3001',
    healthEndpoint: '/',
    status: 'running',
    type: 'frontend'
  },
  {
    id: 'nacos',
    name: 'Nacos',
    description: '服务注册发现中心',
    host: 'localhost',
    port: 8848,
    baseUrl: 'http://localhost:8848',
    healthEndpoint: '/nacos/',
    docsEndpoint: '/nacos/',
    status: 'unknown',
    type: 'infrastructure',
    endpoints: {
      listServices: {
        path: '/nacos/v1/ns/service/list',
        method: 'GET',
        description: '列出所有服务'
      }
    }
  }
]

// 根据ID获取服务配置
export const getServiceConfig = (id: string): ServiceConfig | undefined => {
  return serviceConfigs.find(service => service.id === id)
}

// 获取运行中的服务
export const getRunningServices = (): ServiceConfig[] => {
  return serviceConfigs.filter(service => service.status === 'running')
}

// 获取后端服务
export const getBackendServices = (): ServiceConfig[] => {
  return serviceConfigs.filter(service => service.type === 'backend')
}

// 获取前端服务
export const getFrontendServices = (): ServiceConfig[] => {
  return serviceConfigs.filter(service => service.type === 'frontend')
}

// 获取基础设施服务
export const getInfrastructureServices = (): ServiceConfig[] => {
  return serviceConfigs.filter(service => service.type === 'infrastructure')
}