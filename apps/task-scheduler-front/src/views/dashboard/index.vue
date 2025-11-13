<template>
  <div class="dashboard">
    <!-- 页面头部 -->
    <div class="dashboard-header">
      <h1>微服务监控面板</h1>
      <div class="header-actions">
        <BasicButton type="primary" @click="refreshAllServices" :loading="refreshing">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </BasicButton>
        <BasicButton @click="openSettings">
          <el-icon><Setting /></el-icon>
          设置
        </BasicButton>
      </div>
    </div>

    <!-- 服务状态概览 -->
    <div class="overview-cards">
      <BasicCard v-for="stat in stats" :key="stat.key" class="overview-card" :class="`overview-card--${stat.type}`">
        <div class="overview-card__content">
          <div class="overview-card__icon">
            <el-icon :size="24">
              <component :is="stat.icon" />
            </el-icon>
          </div>
          <div class="overview-card__info">
            <div class="overview-card__value">{{ stat.value }}</div>
            <div class="overview-card__label">{{ stat.label }}</div>
          </div>
        </div>
      </BasicCard>
    </div>

    <!-- 服务列表 -->
    <BasicCard class="services-container">
      <template #header>
        <div class="services-header">
          <h2>服务列表</h2>
          <div class="filter-actions">
            <el-select v-model="serviceFilter" placeholder="筛选服务类型" clearable>
              <el-option label="全部服务" value="" />
              <el-option label="后端服务" value="backend" />
              <el-option label="前端服务" value="frontend" />
              <el-option label="基础设施" value="infrastructure" />
            </el-select>
            <el-select v-model="statusFilter" placeholder="筛选状态" clearable>
              <el-option label="全部状态" value="" />
              <el-option label="运行中" value="running" />
              <el-option label="已停止" value="stopped" />
              <el-option label="未知" value="unknown" />
            </el-select>
          </div>
        </div>
      </template>

      <div class="services-grid">
        <div
          v-for="service in filteredServices"
          :key="service.id"
          class="service-item"
          :class="[
            `service-item--${service.status}`,
            { 'service-item--refreshing': refreshingServices.has(service.id) }
          ]"
        >
          <div class="service-item__header">
            <div class="service-item__info">
              <h3 class="service-item__name">{{ service.name }}</h3>
              <p class="service-item__description">{{ service.description }}</p>
            </div>
            <div class="service-item__status">
              <el-tag
                :type="getStatusTagType(service.status)"
                size="small"
              >
                {{ getStatusText(service.status) }}
              </el-tag>
            </div>
          </div>

          <div class="service-item__details">
            <div class="service-item__endpoint">
              <span class="label">地址:</span>
              <span class="value">{{ service.baseUrl }}</span>
            </div>
            <div class="service-item__endpoint">
              <span class="label">端口:</span>
              <span class="value">{{ service.port }}</span>
            </div>
          </div>

          <div class="service-item__actions">
            <BasicButton
              size="small"
              type="primary"
              @click="checkHealth(service.id)"
              :loading="refreshingServices.has(service.id)"
            >
              检查
            </BasicButton>
            <BasicButton
              v-if="service.docsEndpoint"
              size="small"
              @click="openDocs(service)"
            >
              文档
            </BasicButton>
            <BasicButton
              size="small"
              type="success"
              @click="testApi(service)"
            >
              测试
            </BasicButton>
          </div>
        </div>
      </div>
    </BasicCard>

    <!-- 实时日志 -->
    <BasicCard class="logs-container">
      <template #header>
        <div class="logs-header">
          <h2>实时日志</h2>
          <el-switch
            v-model="autoScroll"
            active-text="自动滚动"
            inactive-text="手动滚动"
          />
        </div>
      </template>

      <div class="logs-content" ref="logsContainer">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-item"
          :class="`log-item--${log.level.toLowerCase()}`"
        >
          <span class="log-time">{{ log.time }}</span>
          <span class="log-level">{{ log.level }}</span>
          <span class="log-source">[{{ log.source }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" class="empty-logs">
          <el-empty description="暂无日志信息" />
        </div>
      </div>
    </BasicCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import { Refresh, Setting, Success, Warning, CircleCloseFilled } from '@element-plus/icons-vue'
import serviceManager from '@/api/service'
import { ServiceConfig } from '@/config/services'
import BasicButton from '@/components/basic/BasicButton.vue'
import BasicCard from '@/components/basic/BasicCard.vue'

// 响应式数据
const refreshing = ref(false)
const refreshingServices = ref(new Set<string>())
const autoScroll = ref(true)
const logsContainer = ref<HTMLElement>()
const logs = ref<Array<{
  time: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
  source: string
  message: string
}>>([])

// 过滤器
const serviceFilter = ref('')
const statusFilter = ref('')

// 服务列表
const allServices = ref<ServiceConfig[]>([])

// 统计数据
const stats = computed(() => {
  const services = allServices.value
  const running = services.filter(s => s.status === 'running').length
  const stopped = services.filter(s => s.status === 'stopped').length
  const unknown = services.filter(s => s.status === 'unknown').length

  return [
    {
      key: 'total',
      label: '总服务数',
      value: services.length,
      icon: 'CircleCloseFilled',
      type: 'info'
    },
    {
      key: 'running',
      label: '运行中',
      value: running,
      icon: 'Success',
      type: 'success'
    },
    {
      key: 'stopped',
      label: '已停止',
      value: stopped,
      icon: 'CircleCloseFilled',
      type: 'danger'
    },
    {
      key: 'unknown',
      label: '未知状态',
      value: unknown,
      icon: 'Warning',
      type: 'warning'
    }
  ]
})

// 过滤后的服务
const filteredServices = computed(() => {
  let services = allServices.value

  if (serviceFilter.value) {
    services = services.filter(service => service.type === serviceFilter.value)
  }

  if (statusFilter.value) {
    services = services.filter(service => service.status === statusFilter.value)
  }

  return services
})

// 获取状态标签类型
const getStatusTagType = (status: string) => {
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

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'running':
      return '运行中'
    case 'stopped':
      return '已停止'
    case 'unknown':
      return '未知'
    default:
      return status
  }
}

// 添加日志
const addLog = (level: string, source: string, message: string) => {
  logs.value.unshift({
    time: new Date().toLocaleTimeString(),
    level,
    source,
    message
  })

  // 限制日志数量
  if (logs.value.length > 100) {
    logs.value = logs.value.slice(0, 100)
  }

  // 自动滚动
  if (autoScroll.value && logsContainer.value) {
    nextTick(() => {
      logsContainer.value.scrollTop = 0
    })
  }
}

// 刷新所有服务状态
const refreshAllServices = async () => {
  refreshing.value = true
  addLog('INFO', 'System', '开始刷新所有服务状态')

  try {
    const { serviceConfigs } = await import('@/config/services')
    allServices.value = serviceConfigs.map((config: ServiceConfig) => ({ ...config }))

    // 并发检查所有服务健康状态
    const healthResults = await serviceManager.checkAllHealth()

    // 更新服务状态
    allServices.value = allServices.value.map(service => ({
      ...service,
      status: healthResults.get(service.id) ? 'running' : 'stopped'
    }))

    const runningCount = Array.from(healthResults.values()).filter(Boolean).length
    addLog('INFO', 'System', `服务状态刷新完成，运行中: ${runningCount}/${allServices.value.length}`)
  } catch (error) {
    console.error('刷新服务状态失败:', error)
    addLog('ERROR', 'System', `刷新服务状态失败: ${error}`)
  } finally {
    refreshing.value = false
  }
}

// 检查单个服务健康状态
const checkHealth = async (serviceId: string) => {
  refreshingServices.value.add(serviceId)

  try {
    const isHealthy = await serviceManager.checkHealth(serviceId)
    const service = allServices.value.find(s => s.id === serviceId)
    if (service) {
      service.status = isHealthy ? 'running' : 'stopped'
    }

    addLog(
      'INFO',
      serviceId,
      `健康检查: ${isHealthy ? '正常' : '异常'}`
    )
  } catch (error) {
    addLog('ERROR', serviceId, `健康检查失败: ${error}`)
  } finally {
    refreshingServices.value.delete(serviceId)
  }
}

// 打开文档
const openDocs = (service: ServiceConfig) => {
  if (service.docsEndpoint) {
    const docsUrl = `${service.baseUrl}${service.docsEndpoint}`
    window.open(docsUrl, '_blank')
    addLog('INFO', service.id, `打开文档: ${docsUrl}`)
  }
}

// 测试API
const testApi = async (service: ServiceConfig) => {
  if (!service.endpoints) {
    ElMessage.info('该服务暂无可测试的API')
    return
  }

  try {
    const firstEndpoint = Object.values(service.endpoints)[0]
    if (firstEndpoint) {
      const response = await serviceManager.request(service.id, {
        method: firstEndpoint.method,
        url: firstEndpoint.path
      })

      addLog(
        'INFO',
        service.id,
        `API测试成功: ${firstEndpoint.description}`
      )

      ElNotification({
        title: 'API测试成功',
        message: `${service.name} - ${firstEndpoint.description}`,
        type: 'success',
        duration: 3000
      })
    }
  } catch (error) {
    addLog('ERROR', service.id, `API测试失败: ${error}`)
    ElMessage.error(`API测试失败: ${error}`)
  }
}

// 打开设置
const openSettings = () => {
  ElMessage.info('设置功能开发中...')
}

// 模拟实时日志
const startLogSimulation = () => {
  const logSources = ['TaskScheduler', 'DataCollector', 'Nacos', 'Frontend']
  const logMessages = [
    '服务启动成功',
    '数据更新完成',
    '健康检查通过',
    'API请求处理',
    '缓存刷新',
    '任务调度执行'
  ]

  // 每5秒添加一条随机日志
  const interval = setInterval(() => {
    const source = logSources[Math.floor(Math.random() * logSources.length)]
    const message = logMessages[Math.floor(Math.random() * logMessages.length)]
    const level = ['INFO', 'DEBUG', 'WARN', 'ERROR'][Math.floor(Math.random() * 4)]

    addLog(level, source, message)
  }, 5000)

  // 组件卸载时清理
  onUnmounted(() => {
    clearInterval(interval)
  })
}

// 组件挂载时初始化
onMounted(() => {
  refreshAllServices()
  startLogSimulation()
})
</script>

<style lang="scss" scoped>
.dashboard {
  padding: var(--spacing-6);
  min-height: 100vh;
  background-color: var(--bg-color);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);

  h1 {
    font-size: 2rem;
    font-weight: 600;
    color: var(--text-color-primary);
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-3);
  }
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
}

.overview-card {
  text-align: center;
  padding: var(--spacing-6);
  transition: transform var(--transition-base);

  &:hover {
    transform: translateY(-2px);
  }

  &__content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-3);
  }

  &__icon {
    width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    margin-bottom: var(--spacing-2);
  }

  &--info {
    .overview-card__icon {
      background-color: rgba(64, 158, 255, 0.1);
      color: var(--primary-color);
    }
  }

  &--success {
    .overview-card__icon {
      background-color: rgba(103, 194, 58, 0.1);
      color: var(--success-color);
    }
  }

  &--danger {
    .overview-card__icon {
      background-color: rgba(245, 108, 108, 0.1);
      color: var(--danger-color);
    }
  }

  &--warning {
    .overview-card__icon {
      background-color: rgba(230, 162, 60, 0.1);
      color: var(--warning-color);
    }
  }

  &__value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-color-primary);
  }

  &__label {
    color: var(--text-color-secondary);
    font-size: var(--font-size-sm);
  }
}

.services-container {
  margin-bottom: var(--spacing-6);
}

.services-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-color-primary);
    margin: 0;
  }

  .filter-actions {
    display: flex;
    gap: var(--spacing-3);
  }
}

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--spacing-4);
}

.service-item {
  padding: var(--spacing-4);
  border: 1px solid var(--border-color-lighter);
  border-radius: var(--border-radius-large);
  transition: all var(--transition-base);

  &:hover {
    box-shadow: var(--shadow-base);
  }

  &--running {
    border-color: var(--success-color);
    background-color: rgba(103, 194, 58, 0.02);
  }

  &--stopped {
    border-color: var(--danger-color);
    background-color: rgba(245, 108, 108, 0.02);
  }

  &--unknown {
    border-color: var(--warning-color);
    background-color: rgba(230, 162, 60, 0.02);
  }

  &--refreshing {
    opacity: 0.6;
  }

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-3);
  }

  &__info {
    flex: 1;

    .service-item__name {
      font-size: var(--font-size-lg);
      font-weight: 600;
      color: var(--text-color-primary);
      margin: 0 0 var(--spacing-1) 0;
    }

    .service-item__description {
      color: var(--text-color-secondary);
      font-size: var(--font-size-sm);
      margin: 0;
      line-height: 1.4;
    }
  }

  &__details {
    margin-bottom: var(--spacing-3);
    font-size: var(--font-size-sm);

    .service-item__endpoint {
      display: flex;
      align-items: center;
      margin-bottom: var(--spacing-1);

      .label {
        width: 60px;
        color: var(--text-color-secondary);
        font-weight: 500;
      }

      .value {
        flex: 1;
        color: var(--text-color-regular);
        font-family: monospace;
      }
    }
  }

  &__actions {
    display: flex;
    gap: var(--spacing-2);
  }
}

.logs-container {
  margin-top: var(--spacing-6);
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-color-primary);
    margin: 0;
  }
}

.logs-content {
  height: 300px;
  overflow-y: auto;
  background-color: #1e1e1e;
  border-radius: var(--border-radius-base);
  padding: var(--spacing-3);
  font-family: monospace;
  font-size: var(--font-size-sm);
}

.log-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-1) 0;
  line-height: 1.4;
  border-bottom: 1px solid #333;

  &:last-child {
    border-bottom: none;
  }

  &--info {
    color: #4FC3F7;
  }

  &--warn {
    color: #FFC107;
  }

  &--error {
    color: #F44336;
  }

  &--debug {
    color: #9E9E9E;
  }

  .log-time {
    width: 80px;
    color: #9E9E9E;
    font-size: var(--font-size-xs);
  }

  .log-level {
    width: 50px;
    font-weight: bold;
  }

  .log-source {
    width: 100px;
    color: #81C784;
  }

  .log-message {
    flex: 1;
    color: #FFFFFF;
  }
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9E9E9E;
}

@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }

  .services-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-header {
    flex-direction: column;
    gap: var(--spacing-4);
    align-items: stretch;
  }

  .services-header {
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .filter-actions {
    flex-direction: column;
    width: 100%;
  }
}
</style>