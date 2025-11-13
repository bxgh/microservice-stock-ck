// 通用类型定义

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
  code?: number
  timestamp?: string
}

// 分页类型
export interface PaginationParams {
  page: number
  pageSize: number
  total?: number
}

export interface PaginationResult<T> {
  list: T[]
  pagination: {
    current: number
    pageSize: number
    total: number
  }
}

// 选项类型
export interface Option<T = string> {
  label: string
  value: T
  disabled?: boolean
}

// 菜单类型
export interface MenuItem {
  id: string
  label: string
  icon?: string
  path?: string
  children?: MenuItem[]
  meta?: {
    title?: string
    icon?: string
    hidden?: boolean
  }
}

// 用户类型
export interface User {
  id: string
  username: string
  email: string
  avatar?: string
  roles: string[]
  permissions: string[]
}

// 表格列类型
export interface TableColumn {
  prop: string
  label: string
  width?: string | number
  minWidth?: string | number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  formatter?: (row: any, column: any, cellValue: any) => string
  slot?: string
}

// 表单字段类型
export interface FormField {
  prop: string
  label: string
  type: 'input' | 'select' | 'radio' | 'checkbox' | 'date' | 'textarea'
  required?: boolean
  placeholder?: string
  options?: Option[]
  rules?: any[]
}

// 主题类型
export type Theme = 'light' | 'dark'

// 尺寸类型
export type Size = 'large' | 'default' | 'small'

// 状态类型
export type Status = 'success' | 'warning' | 'danger' | 'info'

// 组件Props类型
export interface ComponentProps {
  [key: string]: any
}