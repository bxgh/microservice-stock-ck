# API Specification

基于 RESTful API 风格和定义的数据模型：

## REST API Specification

```yaml
openapi: 3.0.0
info:
  title: microservice-stock API
  version: 1.0.0
  description: TaskScheduler 微服务系统 REST API，提供任务管理、调度控制、状态查询和系统监控功能
servers:
  - url: http://localhost:8080/api/v1
    description: 本地开发环境
  - url: http://api-gateway:80/api/v1
    description: Docker Compose 内部环境

paths:
  # Task Management APIs
  /tasks:
    get:
      summary: 获取任务列表
      tags: [Task Management]
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
        - name: status
          in: query
          schema:
            type: string
            enum: [active, inactive, paused, deleted]
        - name: task_type
          in: query
          schema:
            type: string
            enum: [http, shell, plugin]
      responses:
        '200':
          description: 成功返回任务列表
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Task'
                  pagination:
                    $ref: '#/components/schemas/Pagination'

    post:
      summary: 创建新任务
      tags: [Task Management]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTaskRequest'
      responses:
        '201':
          description: 任务创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '400':
          description: 请求参数错误
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /tasks/{task_id}:
    get:
      summary: 获取任务详情
      tags: [Task Management]
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: 成功返回任务详情
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '404':
          description: 任务不存在
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Task Control APIs
  /tasks/{task_id}/start:
    post:
      summary: 启动任务
      tags: [Task Control]
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: 任务启动成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskControlResponse'

  # System Monitoring APIs
  /system/health:
    get:
      summary: 系统健康检查
      tags: [System Monitoring]
      responses:
        '200':
          description: 系统健康状态
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SystemHealth'

components:
  schemas:
    Task:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        task_type:
          type: string
          enum: [http, shell, plugin]
        status:
          type: string
          enum: [active, inactive, paused, deleted]
        schedule_config:
          $ref: '#/components/schemas/ScheduleConfig'
        execution_config:
          $ref: '#/components/schemas/ExecutionConfig'
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    CreateTaskRequest:
      type: object
      required: [name, task_type, schedule_config, execution_config]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        task_type:
          type: string
          enum: [http, shell, plugin]
        schedule_config:
          $ref: '#/components/schemas/ScheduleConfig'
        execution_config:
          $ref: '#/components/schemas/ExecutionConfig'

    ScheduleConfig:
      type: object
      required: [timezone, retry_config]
      properties:
        cron_expression:
          type: string
          description: Cron 表达式
        interval_seconds:
          type: integer
          minimum: 1
          description: 间隔调度秒数
        timezone:
          type: string
          description: 时区
        retry_config:
          $ref: '#/components/schemas/RetryConfig'

    ExecutionConfig:
      type: object
      required: [timeout_seconds, max_retries, retry_delay_seconds]
      properties:
        timeout_seconds:
          type: integer
          minimum: 1
          maximum: 86400
        max_retries:
          type: integer
          minimum: 0
          maximum: 10
        retry_delay_seconds:
          type: integer
          minimum: 1

    RetryConfig:
      type: object
      required: [max_attempts, delay_seconds]
      properties:
        max_attempts:
          type: integer
          minimum: 0
          maximum: 10
        delay_seconds:
          type: integer
          minimum: 1
        backoff_multiplier:
          type: number
          minimum: 1.0
          maximum: 10.0
          default: 2.0

    TaskControlResponse:
      type: object
      properties:
        success:
          type: boolean
        message:
          type: string
        task_id:
          type: string
        current_status:
          type: string
        timestamp:
          type: string
          format: date-time

    Pagination:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer
        total_pages:
          type: integer

    SystemHealth:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, unhealthy, degraded]
        services:
          type: object
          additionalProperties:
            type: object
            properties:
              status:
                type: string
                enum: [up, down, degraded]
              response_time_ms:
                type: number
              last_check:
                type: string
                format: date-time
        timestamp:
          type: string
          format: date-time

    ErrorResponse:
      type: object
      required: [error]
      properties:
        error:
          type: object
          required: [code, message, timestamp, requestId]
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: object
            timestamp:
              type: string
              format: date-time
            requestId:
              type: string
```
