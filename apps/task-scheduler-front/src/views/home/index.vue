<template>
  <div class="home">
    <!-- Hero 区域 -->
    <div class="hero">
      <div class="hero__content">
        <h1 class="hero__title">Frontend Template</h1>
        <p class="hero__subtitle">企业级前端模板框架</p>
        <p class="hero__description">
          基于 Vue 3 + TypeScript + Element Plus 构建的现代化前端模板
        </p>
        <div class="hero__actions">
          <BasicButton type="primary" size="large" @click="goToComponents">
            开始使用
          </BasicButton>
          <BasicButton size="large" @click="goToExamples">
            查看示例
          </BasicButton>
        </div>
      </div>
    </div>

    <!-- 特性介绍 -->
    <div class="features">
      <div class="container">
        <h2 class="section-title">核心特性</h2>
        <div class="features__grid">
          <BasicCard hoverable v-for="feature in features" :key="feature.id">
            <div class="feature-item">
              <div class="feature__icon">
                <el-icon :size="32">
                  <component :is="feature.icon" />
                </el-icon>
              </div>
              <h3 class="feature__title">{{ feature.title }}</h3>
              <p class="feature__description">{{ feature.description }}</p>
            </div>
          </BasicCard>
        </div>
      </div>
    </div>

    <!-- 技术栈 -->
    <div class="tech-stack">
      <div class="container">
        <h2 class="section-title">技术栈</h2>
        <div class="tech-list">
          <el-tag
            v-for="tech in techStack"
            :key="tech.name"
            :type="tech.type"
            size="large"
            class="tech-tag"
          >
            {{ tech.name }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Star, Trophy, Lightning, Setting
} from '@element-plus/icons-vue'
import BasicButton from '@/components/basic/BasicButton.vue'
import BasicCard from '@/components/basic/BasicCard.vue'

const router = useRouter()

const features = ref([
  {
    id: 1,
    title: '现代化架构',
    description: '基于 Vue 3 Composition API + TypeScript，提供类型安全的开发体验',
    icon: Star
  },
  {
    id: 2,
    title: '组件库',
    description: '丰富的组件库，包含基础组件、布局组件和业务组件',
    icon: Trophy
  },
  {
    id: 3,
    title: '开发工具',
    description: '完整的开发工具链，支持 ESLint、Prettier、Vitest 等工具',
    icon: Lightning
  },
  {
    id: 4,
    title: '最佳实践',
    description: '遵循前端开发最佳实践，提供规范的项目结构和代码风格',
    icon: Setting
  }
])

const techStack = ref([
  { name: 'Vue 3.4+', type: 'primary' },
  { name: 'TypeScript 5.0+', type: 'success' },
  { name: 'Element Plus', type: 'warning' },
  { name: 'Vite 5.0+', type: 'danger' },
  { name: 'Pinia', type: 'info' },
  { name: 'Vue Router 4', type: '' },
  { name: 'SCSS', type: 'primary' },
  { name: 'ESLint', type: 'success' },
  { name: 'Prettier', type: 'warning' },
  { name: 'Vitest', type: 'danger' }
])

const goToComponents = () => {
  router.push('/components')
}

const goToExamples = () => {
  router.push('/examples')
}
</script>

<style lang="scss" scoped>
.home {
  min-height: 100vh;
}

.hero {
  height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-align: center;

  &__content {
    max-width: 800px;
    padding: 0 var(--spacing-6);
  }

  &__title {
    font-size: 4rem;
    font-weight: 700;
    margin-bottom: var(--spacing-4);
    animation: fadeInUp 0.8s ease-out;
  }

  &__subtitle {
    font-size: 1.5rem;
    margin-bottom: var(--spacing-3);
    opacity: 0.9;
    animation: fadeInUp 0.8s ease-out 0.2s backwards;
  }

  &__description {
    font-size: 1.1rem;
    margin-bottom: var(--spacing-8);
    opacity: 0.8;
    line-height: 1.6;
    animation: fadeInUp 0.8s ease-out 0.4s backwards;
  }

  &__actions {
    display: flex;
    gap: var(--spacing-4);
    justify-content: center;
    animation: fadeInUp 0.8s ease-out 0.6s backwards;
  }
}

.features {
  padding: var(--spacing-20) 0;
  background-color: var(--bg-color-page);

  &__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: var(--spacing-6);
    margin-top: var(--spacing-8);
  }
}

.feature-item {
  text-align: center;
  padding: var(--spacing-6);

  &__icon {
    margin-bottom: var(--spacing-4);
    color: var(--primary-color);
  }

  &__title {
    font-size: var(--font-size-xl);
    font-weight: 600;
    margin-bottom: var(--spacing-3);
    color: var(--text-color-primary);
  }

  &__description {
    color: var(--text-color-secondary);
    line-height: 1.6;
  }
}

.tech-stack {
  padding: var(--spacing-20) 0;
  background-color: var(--bg-color);

  .tech-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-3);
    justify-content: center;
    margin-top: var(--spacing-8);
  }

  .tech-tag {
    font-size: var(--font-size-lg);
    padding: var(--spacing-3) var(--spacing-4);
  }
}

.section-title {
  text-align: center;
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--text-color-primary);
  margin-bottom: var(--spacing-4);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--spacing-6);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .hero {
    &__title {
      font-size: 2.5rem;
    }

    &__subtitle {
      font-size: 1.2rem;
    }

    &__actions {
      flex-direction: column;
      align-items: center;
    }
  }

  .features__grid {
    grid-template-columns: 1fr;
  }

  .section-title {
    font-size: 2rem;
  }
}
</style>