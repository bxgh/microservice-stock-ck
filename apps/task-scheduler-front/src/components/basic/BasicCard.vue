<template>
  <el-card
    :class="[
      'basic-card',
      {
        'basic-card--bordered': bordered,
        'basic-card--shadow': shadow,
        'basic-card--hoverable': hoverable
      }
    ]"
    :body-style="bodyStyle"
  >
    <template #header v-if="$slots.header">
      <div class="basic-card__header">
        <slot name="header" />
        <el-button
          v-if="closable"
          type="text"
          size="small"
          @click="handleClose"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </template>

    <div class="basic-card__content">
      <slot />
    </div>

    <template #footer v-if="$slots.footer">
      <div class="basic-card__footer">
        <slot name="footer" />
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { Close } from '@element-plus/icons-vue'

interface CardProps {
  bordered?: boolean
  shadow?: boolean | string
  hoverable?: boolean
  closable?: boolean
  bodyStyle?: Record<string, any>
}

withDefaults(defineProps<CardProps>(), {
  bordered: true,
  shadow: 'always',
  hoverable: false,
  closable: false,
  bodyStyle: () => ({})
})

const emit = defineEmits<{
  close: []
}>()

const handleClose = () => {
  emit('close')
}
</script>

<style lang="scss" scoped>
.basic-card {
  transition: all var(--transition-base) var(--transition-timing);
  border-radius: var(--border-radius-large);

  &--bordered {
    border: 1px solid var(--border-color-light);
  }

  &--shadow {
    box-shadow: var(--shadow-base);
  }

  &--hoverable {
    &:hover {
      box-shadow: var(--shadow-lg);
      transform: translateY(-2px);
    }
  }

  :deep(.el-card__header) {
    padding: var(--spacing-4) var(--spacing-6);
    border-bottom: 1px solid var(--border-color-lighter);
    background-color: var(--bg-color-page);
  }

  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
    color: var(--text-color-primary);
  }

  :deep(.el-card__body) {
    padding: var(--spacing-6);
  }

  &__content {
    color: var(--text-color-regular);
  }

  :deep(.el-card__footer) {
    padding: var(--spacing-4) var(--spacing-6);
    border-top: 1px solid var(--border-color-lighter);
    background-color: var(--bg-color-page);
  }

  &__footer {
    color: var(--text-color-secondary);
    font-size: var(--font-size-sm);
  }
}
</style>