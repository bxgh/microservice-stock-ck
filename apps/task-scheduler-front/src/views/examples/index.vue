<template>
  <div class="examples-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>示例页面</h1>
      <p>Frontend Template 框架的使用示例</p>
    </div>

    <!-- 示例导航 -->
    <div class="example-nav">
      <el-tabs v-model="activeTab" type="card">
        <el-tab-pane label="基础示例" name="basic">
          <span>基础功能使用示例</span>
        </el-tab-pane>
        <el-tab-pane label="高级示例" name="advanced">
          <span>高级功能展示</span>
        </el-tab-pane>
        <el-tab-pane label="集成示例" name="integration">
          <span>微服务集成示例</span>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 示例内容 -->
    <div class="example-content">
      <div v-if="activeTab === 'basic'" class="example-section">
        <h2>基础示例</h2>
        <p>这里展示了 Frontend Template 框架的基础功能使用方法。</p>

        <div class="example-grid">
          <BasicCard>
            <template #header>响应式布局</template>
            <p>这是一个响应式的卡片组件，可以自适应不同屏幕尺寸。</p>
          </BasicCard>

          <BasicCard>
            <template #header>主题切换</template>
            <p>支持亮色/暗色主题切换，提供更好的用户体验。</p>
          </BasicCard>
        </div>
      </div>

      <div v-if="activeTab === 'advanced'" class="example-section">
        <h2>高级示例</h2>
        <p>展示框架的高级功能和复杂组件的使用。</p>

        <div class="example-grid">
          <BasicCard>
            <template #header>数据可视化</template>
            <p>集成 ECharts 图表库，提供丰富的数据可视化组件。</p>
          </BasicCard>

          <BasicCard>
            <template #header>表单验证</template>
            <p>完整的表单验证系统，支持多种验证规则。</p>
          </BasicCard>
        </div>
      </div>

      <div v-if="activeTab === 'integration'" class="example-section">
        <h2>微服务集成示例</h2>
        <p>展示如何与微服务后端进行集成。</p>

        <div class="example-grid">
          <BasicCard>
            <template #header>API 调用</template>
            <p>统一的 API 客户端，支持多个微服务的调用和管理。</p>
          </BasicCard>

          <BasicCard>
            <template #header>服务监控</template>
            <p>实时监控各个微服务的状态和健康检查。</p>
          </BasicCard>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import BasicCard from '@/components/basic/BasicCard.vue'

// 响应式数据
const activeTab = ref('basic')
</script>

<style lang="scss" scoped>
.examples-page {
  padding: var(--spacing-6);
  min-height: 100vh;
  background-color: var(--bg-color);
}

.page-header {
  text-align: center;
  margin-bottom: var(--spacing-6);

  h1 {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text-color-primary);
    margin-bottom: var(--spacing-2);
  }

  p {
    color: var(--text-color-secondary);
    font-size: var(--font-size-lg);
  }
}

.example-nav {
  margin-bottom: var(--spacing-6);
}

.example-content {
  margin-top: var(--spacing-4);
}

.example-section {
  margin-bottom: var(--spacing-8);

  h2 {
    font-size: 1.8rem;
    font-weight: 600;
    color: var(--text-color-primary);
    margin-bottom: var(--spacing-4);
  }

  p {
    color: var(--text-color-secondary);
    margin-bottom: var(--spacing-4);
    font-size: var(--font-size-base);
  }
}

.example-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--spacing-6);
}

@media (max-width: 768px) {
  .example-grid {
    grid-template-columns: 1fr;
  }
}
</style>