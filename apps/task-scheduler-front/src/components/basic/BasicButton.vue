<template>
  <el-button
    :type="type"
    :size="size"
    :loading="loading"
    :disabled="disabled"
    :icon="icon"
    :plain="plain"
    :round="round"
    :circle="circle"
    :class="[
      'basic-button',
      `basic-button--${type}`,
      `basic-button--${size}`
    ]"
    @click="handleClick"
  >
    <slot />
  </el-button>
</template>

<script setup lang="ts">
import { ComponentProps } from '@/types'

interface ButtonProps {
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'text' | 'default'
  size?: 'large' | 'default' | 'small'
  loading?: boolean
  disabled?: boolean
  icon?: string
  plain?: boolean
  round?: boolean
  circle?: boolean
}

withDefaults(defineProps<ButtonProps>(), {
  type: 'default',
  size: 'default',
  loading: false,
  disabled: false,
  plain: false,
  round: false,
  circle: false
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const handleClick = (event: MouseEvent) => {
  emit('click', event)
}
</script>

<style lang="scss" scoped>
.basic-button {
  transition: all var(--transition-base) var(--transition-timing);

  &--primary {
    &:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
  }

  &--success {
    &:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
  }

  &--warning {
    &:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
  }

  &--danger {
    &:hover {
      transform: translateY(-1px);
      box-shadow: var(--shadow-md);
    }
  }

  &:active {
    transform: translateY(0);
  }
}
</style>