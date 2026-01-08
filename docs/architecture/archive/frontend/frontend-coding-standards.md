# Frontend Coding Standards

## 🎨 Vue 3 + TypeScript Standards

### Component Structure
```vue
<template>
  <!-- Template content with Element Plus components -->
</template>

<script setup lang="ts">
// Imports
import { ref, computed, onMounted } from 'vue'
import type { ComponentProps } from '@/types'

// Props interface
interface Props {
  title: string
  items: Item[]
  loading?: boolean
}

// Props definition
const props = withDefaults(defineProps<Props>(), {
  loading: false
})

// Emits
interface Emits {
  update: [value: string]
  delete: [id: string]
}

const emit = defineEmits<Emits>()

// Reactive state
const count = ref(0)
const isLoading = ref(false)

// Computed properties
const formattedItems = computed(() => {
  return props.items.map(item => ({
    ...item,
    formattedTitle: item.title.toUpperCase()
  }))
})

// Methods
const handleUpdate = (value: string) => {
  emit('update', value)
}

// Lifecycle
onMounted(() => {
  // Initialization logic
})
</script>

<style scoped lang="scss">
// Component-specific styles
@import '@/styles/variables.scss';

.component {
  // Styles using SCSS variables
}
</style>
```

### TypeScript Standards

#### Type Definitions
```typescript
// Use interfaces for object shapes
interface User {
  id: string
  name: string
  email: string
  role: UserRole
}

// Use unions for constrained values
type UserRole = 'admin' | 'user' | 'viewer'

// Use generics for reusable types
interface ApiResponse<T> {
  data: T
  status: number
  message: string
}

// Pinia store type
interface UserStore {
  users: User[]
  currentUser: User | null
  loading: boolean
  fetchUsers: () => Promise<void>
  createUser: (user: Omit<User, 'id'>) => Promise<void>
}
```

#### Component Props
```typescript
// Always define prop interfaces
interface ButtonProps {
  type?: 'primary' | 'secondary' | 'danger'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  loading?: boolean
}

// Use withDefaults for default values
const props = withDefaults(defineProps<ButtonProps>(), {
  type: 'primary',
  size: 'medium',
  disabled: false,
  loading: false
})
```

### Element Plus Integration

#### Component Usage
```vue
<template>
  <el-button
    :type="props.type"
    :size="props.size"
    :disabled="props.disabled"
    :loading="props.loading"
    @click="handleClick"
  >
    <slot />
  </el-button>
</template>

<script setup lang="ts">
import { ElButton } from 'element-plus'

interface Props {
  type?: 'primary' | 'secondary' | 'danger'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'primary',
  size: 'medium'
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const handleClick = (event: MouseEvent) => {
  emit('click', event)
}
</script>
```

#### Form Validation
```vue
<template>
  <el-form
    ref="formRef"
    :model="formModel"
    :rules="formRules"
    label-width="120px"
  >
    <el-form-item label="Name" prop="name">
      <el-input v-model="formModel.name" />
    </el-form-item>

    <el-form-item label="Email" prop="email">
      <el-input v-model="formModel.email" type="email" />
    </el-form-item>

    <el-form-item>
      <el-button type="primary" @click="submitForm">
        Submit
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import type { FormInstance, FormRules } from 'element-plus'

interface FormModel {
  name: string
  email: string
}

const formRef = ref<FormInstance>()
const formModel = reactive<FormModel>({
  name: '',
  email: ''
})

const formRules: FormRules<FormModel> = {
  name: [
    { required: true, message: 'Please enter name', trigger: 'blur' },
    { min: 2, max: 50, message: 'Length should be 2 to 50', trigger: 'blur' }
  ],
  email: [
    { required: true, message: 'Please enter email', trigger: 'blur' },
    { type: 'email', message: 'Please enter correct email', trigger: 'blur' }
  ]
}

const submitForm = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    // Submit logic
  } catch (error) {
    console.error('Validation failed:', error)
  }
}
</script>
```

### State Management (Pinia)

#### Store Definition
```typescript
// stores/user.ts
import { defineStore } from 'pinia'
import type { User } from '@/types'

interface UserState {
  users: User[]
  currentUser: User | null
  loading: boolean
  error: string | null
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    users: [],
    currentUser: null,
    loading: false,
    error: null
  }),

  getters: {
    userCount: (state) => state.users.length,
    activeUsers: (state) => state.users.filter(user => user.active),
    userById: (state) => (id: string) => state.users.find(user => user.id === id)
  },

  actions: {
    async fetchUsers() {
      this.loading = true
      this.error = null

      try {
        const response = await userApi.getUsers()
        this.users = response.data
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to fetch users'
        throw error
      } finally {
        this.loading = false
      }
    },

    async createUser(userData: Omit<User, 'id'>) {
      try {
        const response = await userApi.createUser(userData)
        this.users.push(response.data)
        return response.data
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to create user'
        throw error
      }
    }
  }
})
```

### Composables

#### Reusable Logic
```typescript
// composables/useApi.ts
import { ref, computed } from 'vue'

export function useApi<T>() {
  const data = ref<T | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isLoading = computed(() => loading.value)
  const hasError = computed(() => !!error.value)
  const hasData = computed(() => data.value !== null)

  const execute = async (apiCall: () => Promise<T>) => {
    loading.value = true
    error.value = null

    try {
      data.value = await apiCall()
      return data.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An error occurred'
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    data.value = null
    error.value = null
    loading.value = false
  }

  return {
    data: readonly(data),
    loading: readonly(loading),
    error: readonly(error),
    isLoading,
    hasError,
    hasData,
    execute,
    reset
  }
}
```

### CSS/SCSS Standards

#### Component Styling
```scss
<style scoped lang="scss">
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.component {
  // Use SCSS variables
  padding: $spacing-md;
  border-radius: $border-radius-md;

  // Use mixins
  @include flex-center;

  // Responsive design
  @include respond-to('mobile') {
    padding: $spacing-sm;
  }

  // State-based styling
  &--loading {
    opacity: 0.6;
    pointer-events: none;
  }

  // Child elements
  &__title {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    margin-bottom: $spacing-sm;
  }

  &__content {
    color: $text-color-secondary;
  }
}
</style>
```

## 📏 Code Quality Rules

### ESLint Configuration
- Use @typescript-eslint/parser
- Enable vue/vue3-recommended rules
- Enforce consistent naming conventions
- Require TypeScript types for all functions

### Testing Standards
- Write tests for all components
- Use Vitest + Vue Test Utils
- Test user interactions
- Test edge cases and error states
- Maintain >80% code coverage

### Performance Guidelines
- Use `v-memo` for expensive components
- Implement lazy loading
- Optimize bundle size
- Use computed properties efficiently
- Avoid unnecessary re-renders