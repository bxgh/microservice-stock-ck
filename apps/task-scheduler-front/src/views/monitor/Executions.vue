<template>
  <div class="executions">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>执行记录</span>
          <el-button type="primary" @click="refreshData">刷新</el-button>
        </div>
      </template>

      <el-table :data="executions" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="task_name" label="任务名称" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="180" />
        <el-table-column prop="duration" label="耗时" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const loading = ref(false)
const executions = ref([
  { id: 1, task_name: '数据同步', status: 'success', start_time: '2024-01-15 10:00:00', duration: '45s' },
  { id: 2, task_name: '邮件发送', status: 'failed', start_time: '2024-01-15 09:30:00', duration: '120s' }
])

const getStatusType = (status: string) => {
  return status === 'success' ? 'success' : 'danger'
}

const refreshData = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 1000)
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
</style>