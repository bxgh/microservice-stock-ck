<template>
  <div class="performance">
    <el-card>
      <template #header>
        <span>性能监控</span>
      </template>
      <div class="performance-content">
        <h3>系统性能指标</h3>
        <p>CPU使用率: 45%</p>
        <p>内存使用率: 67%</p>
        <p>任务队列长度: 12</p>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 性能监控组件
</script>

<style scoped>
.performance-content h3 {
  margin-bottom: 16px;
}

.performance-content p {
  margin-bottom: 8px;
}
</style>