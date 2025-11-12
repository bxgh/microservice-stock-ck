<template>
  <div class="logs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统日志</span>
          <el-button type="primary" @click="refreshLogs">刷新</el-button>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getLogLevelType(row.level)">
              {{ row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const loading = ref(false)
const logs = ref([
  { timestamp: '2024-01-15 10:30:15', level: 'INFO', message: 'Task "数据同步任务" executed successfully' },
  { timestamp: '2024-01-15 10:25:32', level: 'WARNING', message: 'Task "邮件发送任务" timeout after 120 seconds' },
  { timestamp: '2024-01-15 10:20:10', level: 'ERROR', message: 'Database connection failed' }
])

const getLogLevelType = (level: string) => {
  const levelMap = {
    'INFO': 'info',
    'WARNING': 'warning',
    'ERROR': 'danger'
  }
  return levelMap[level] || 'info'
}

const refreshLogs = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 1000)
}

onMounted(() => {
  refreshLogs()
})
</script>

<style scoped>
.logs .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>