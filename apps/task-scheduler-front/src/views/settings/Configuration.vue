<template>
  <div class="configuration">
    <el-card>
      <template #header>
        <span>系统配置</span>
      </template>
      <el-form :model="config" label-width="120px">
        <el-form-item label="最大并发数">
          <el-input-number v-model="config.maxConcurrency" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="默认超时时间">
          <el-input-number v-model="config.defaultTimeout" :min="60" :max="3600" />
          <span class="unit">秒</span>
        </el-form-item>
        <el-form-item label="日志级别">
          <el-select v-model="config.logLevel">
            <el-option label="DEBUG" value="debug" />
            <el-option label="INFO" value="info" />
            <el-option label="WARNING" value="warning" />
            <el-option label="ERROR" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

const config = reactive({
  maxConcurrency: 10,
  defaultTimeout: 300,
  logLevel: 'info'
})

const saveConfig = () => {
  ElMessage.success('配置保存成功')
}
</script>

<style scoped>
.unit {
  margin-left: 8px;
  color: #909399;
}
</style>