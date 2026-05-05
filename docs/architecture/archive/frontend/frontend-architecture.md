# Frontend Architecture

## Component Organization
```
microservice-stock/services/web-ui/src/
├── components/           # 可复用组件
│   ├── common/          # 通用组件
│   ├── tasks/           # 任务相关组件
│   └── dashboard/       # 仪表板组件
├── pages/               # 页面组件 (路由)
│   ├── Tasks/           # 任务管理页面
│   ├── Dashboard/       # 仪表板页面
│   ├── DataSources/     # 数据源管理页面
│   ├── Monitoring/      # 监控页面
│   └── Settings/        # 设置页面
├── hooks/               # 自定义 React Hooks
├── services/            # API 客户端服务
├── stores/              # Zustand 状态管理
├── types/               # TypeScript 类型定义
├── utils/               # 工具函数
└── styles/              # 样式文件
```

## State Management Structure
```typescript
// stores/tasksStore.ts
interface TasksState {
  // State
  tasks: Task[];
  selectedTask: Task | null;
  executions: TaskExecution[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchTasks: () => Promise<void>;
  createTask: (task: CreateTaskRequest) => Promise<void>;
  updateTask: (id: string, task: Partial<Task>) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  startTask: (id: string) => Promise<void>;
  stopTask: (id: string) => Promise<void>;
}
```
