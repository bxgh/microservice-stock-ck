<template>
  <div class="task-create">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <h2 class="page-title">创建任务</h2>
        <div class="header-actions">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" @click="handleSave" :loading="saving">
            保存
          </el-button>
        </div>
      </div>
    </div>

    <!-- 表单内容 -->
    <el-card class="form-card" shadow="never">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        size="large"
      >
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="任务名称" prop="name">
              <el-input
                v-model="form.name"
                placeholder="请输入任务名称"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="任务类型" prop="task_type">
              <el-select v-model="form.task_type" placeholder="请选择任务类型">
                <el-option label="HTTP请求" value="http" />
                <el-option label="Shell脚本" value="shell" />
                <el-option label="Python脚本" value="python" />
                <el-option label="数据库操作" value="database" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="任务描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入任务描述"
          />
        </el-form-item>

        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="调度规则" prop="cron_expression">
              <el-input
                v-model="form.cron_expression"
                placeholder="0 * * * *"
                clearable
              >
                <template #append>
                  <el-button @click="showCronHelper">帮助</el-button>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用状态" prop="enabled">
              <el-switch
                v-model="form.enabled"
                active-text="启用"
                inactive-text="禁用"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 任务配置区域 -->
        <el-divider content-position="left">任务配置</el-divider>

        <!-- HTTP任务配置 -->
        <div v-if="form.type === 'http'" class="task-config">
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="请求URL" prop="config.url">
                <el-input
                  v-model="form.config.url"
                  placeholder="https://api.example.com/endpoint"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="请求方法" prop="config.method">
                <el-select v-model="form.config.method">
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="DELETE" value="DELETE" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="请求头">
            <el-input
              v-model="form.config.headers"
              type="textarea"
              :rows="2"
              placeholder='{"Content-Type": "application/json"}'
            />
          </el-form-item>
          <el-form-item label="请求体">
            <el-input
              v-model="form.config.body"
              type="textarea"
              :rows="3"
              placeholder='{"key": "value"}'
            />
          </el-form-item>
        </div>

        <!-- Shell任务配置 -->
        <div v-else-if="form.type === 'shell'" class="task-config">
          <el-form-item label="Shell脚本" prop="config.script">
            <el-input
              v-model="form.config.script"
              type="textarea"
              :rows="6"
              placeholder="#!/bin/bash&#10;echo 'Hello World'"
            />
          </el-form-item>
        </div>

        <!-- Python任务配置 -->
        <div v-else-if="form.type === 'python'" class="task-config">
          <el-form-item label="Python脚本" prop="config.script">
            <el-input
              v-model="form.config.script"
              type="textarea"
              :rows="6"
              placeholder="print('Hello World')"
            />
          </el-form-item>
        </div>

        <!-- 超时和重试配置 -->
        <el-divider content-position="left">高级配置</el-divider>
        <el-row :gutter="24">
          <el-col :span="8">
            <el-form-item label="超时时间(秒)" prop="timeout">
              <el-input-number
                v-model="form.timeout"
                :min="1"
                :max="3600"
                controls-position="right"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="重试次数" prop="max_retries">
              <el-input-number
                v-model="form.max_retries"
                :min="0"
                :max="5"
                controls-position="right"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="重试延迟(秒)" prop="retry_delay">
              <el-input-number
                v-model="form.retry_delay"
                :min="1"
                :max="300"
                controls-position="right"
              />
            </el-form-item>
          </el-col>
        </el-row>

              <!-- 标签配置 -->
        <el-divider content-position="left">标签配置</el-divider>
        <el-form-item label="任务标签">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="添加标签（可选）"
          >
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Cron表达式帮助对话框 -->
    <el-dialog
      v-model="cronHelperVisible"
      title="Cron表达式帮助"
      width="60%"
    >
      <div class="cron-help">
        <h4>Cron表达式格式：分 时 日 月 星期</h4>
        <el-table :data="cronExamples" stripe>
          <el-table-column prop="expression" label="表达式" width="120" />
          <el-table-column prop="description" label="说明" />
        </el-table>
        <div class="cron-tips">
          <p><strong>特殊字符说明：</strong></p>
          <ul>
            <li><code>*</code> : 任意值</li>
            <li><code>,</code> : 多个值用逗号分隔</li>
            <li><code>-</code> : 范围 (如：1-5)</li>
            <li><code>/</code> : 步长 (如：*/5 每5分钟)</li>
          </ul>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElForm } from 'element-plus'
import type { FormRules } from 'element-plus'
import taskSchedulerApi, { type TaskCreateRequest, type TaskConfig } from '@/api/taskScheduler'

// 响应式数据
const router = useRouter()
const formRef = ref<InstanceType<typeof ElForm>>()
const saving = ref(false)
const cronHelperVisible = ref(false)

// 表单数据 - 为了UI友好，使用内部结构
const form = reactive({
  name: '',
  task_type: 'http',
  description: '',
  cron_expression: '',
  config: {
    url: '',
    method: 'GET',
    headers: '',
    body: '',
    script: ''
  },
  timeout: 300,
  max_retries: 3,
  retry_delay: 60,
  enabled: true,
  tags: []
})

// 表单验证规则
const rules: FormRules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { min: 2, max: 50, message: '任务名称长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  task_type: [
    { required: true, message: '请选择任务类型', trigger: 'change' }
  ],
  cron_expression: [
    { required: true, message: '请输入调度规则', trigger: 'blur' }
  ],
  'config.url': [
    { required: true, message: '请输入请求URL', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL', trigger: 'blur' }
  ],
  'config.script': [
    { required: true, message: '请输入脚本内容', trigger: 'blur' }
  ]
}

// Cron表达式示例
const cronExamples = [
  { expression: '*/5 * * * *', description: '每5分钟执行一次' },
  { expression: '0 */1 * * *', description: '每小时执行一次' },
  { expression: '0 0 */1 * *', description: '每天执行一次' },
  { expression: '0 0 * * 0', description: '每周执行一次' },
  { expression: '0 0 1 * *', description: '每月执行一次' },
  { expression: '0 9 * * 1-5', description: '工作日上午9点执行' }
]

// 显示Cron帮助
const showCronHelper = () => {
  cronHelperVisible.value = true
}

// 取消创建
const handleCancel = () => {
  router.push('/tasks/list')
}

// 保存任务
const handleSave = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    saving.value = true

    // 处理表单数据
    // 将结构化的config转换为API要求的字符串格式
    const config: TaskConfig = {}

    if (form.config.url) config.url = form.config.url
    if (form.config.method) config.method = form.config.method
    if (form.config.headers) config.headers = form.config.headers
    if (form.config.body) config.body = form.config.body
    if (form.config.script) config.script = form.config.script

    const taskData: TaskCreateRequest = {
      name: form.name,
      description: form.description,
      cron_expression: form.cron_expression,
      task_type: form.task_type,
      config,
      timeout: form.timeout,
      max_retries: form.max_retries,
      retry_delay: form.retry_delay,
      enabled: form.enabled,
      tags: form.tags
    }

    console.log('创建任务:', taskData)
    await taskSchedulerApi.createTask(taskData)

    router.push('/tasks/list')
  } catch (error) {
    console.error('创建任务失败:', error)
  } finally {
    saving.value = false
  }
}

// 组件挂载
onMounted(() => {
  // 初始化表单
})
</script>

<style lang="scss" scoped>
.task-create {
  .page-header {
    margin-bottom: 20px;

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .page-title {
        font-size: 24px;
        font-weight: 600;
        color: #303133;
        margin: 0;
      }

      .header-actions {
        display: flex;
        gap: 12px;
      }
    }
  }

  .form-card {
    max-width: 1000px;

    .task-config {
      background-color: #f8f9fa;
      padding: 20px;
      border-radius: 6px;
      margin-bottom: 20px;
    }
  }
}

.cron-help {
  h4 {
    margin-bottom: 16px;
    color: #303133;
  }

  .cron-tips {
    margin-top: 20px;
    padding: 16px;
    background-color: #f0f9ff;
    border-radius: 6px;
    border-left: 4px solid #409eff;

    p {
      margin-bottom: 12px;
    }

    ul {
      margin: 0;
      padding-left: 20px;

      li {
        margin-bottom: 8px;

        code {
          background-color: #f5f5f5;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: 'Courier New', monospace;
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .task-create {
    .page-header .header-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;

      .header-actions {
        width: 100%;
        justify-content: flex-end;
      }
    }

    :deep(.el-row) {
      margin: 0 !important;

      .el-col {
        padding: 0 !important;
        margin-bottom: 20px;
      }
    }
  }
}
</style>