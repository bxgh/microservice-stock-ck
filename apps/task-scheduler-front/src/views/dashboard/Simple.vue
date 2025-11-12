<template>
  <div class="simple-dashboard">
    <el-card>
      <template #header>
        <h2>Task Scheduler 仪表板</h2>
      </template>
      <p>欢迎使用Task Scheduler管理系统！</p>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-content">
              <h3>总任务数</h3>
              <div class="stat-value">156</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-content">
              <h3>运行中</h3>
              <div class="stat-value">12</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-content">
              <h3>成功率</h3>
              <div class="stat-value">94.8%</div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 简单的仪表板页面
</script>

<style scoped>
.simple-dashboard {
  padding: 20px;
}

.stat-card {
  text-align: center;
  margin-bottom: 20px;
}

.stat-content h3 {
  margin-bottom: 10px;
  color: #666;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}
</style>