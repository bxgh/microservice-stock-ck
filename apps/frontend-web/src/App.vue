<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

// 移除加载动画
onMounted(() => {
  const loadingElement = document.getElementById('loading')
  if (loadingElement) {
    loadingElement.remove()
  }
})
</script>

<style lang="scss">
// 全局样式重置
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  background-color: #f5f5f5;
}

#app {
  height: 100vh;
  overflow: hidden;
}

// Element Plus 样式覆盖
.el-table .cell {
  word-break: break-word;
}

.el-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

// 自定义滚动条
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

// 工具类
.text-center {
  text-align: center;
}

.text-right {
  text-align: right;
}

.flex {
  display: flex;
}

.flex-center {
  display: flex;
  justify-content: center;
  align-items: center;
}

.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.w-full {
  width: 100%;
}

.h-full {
  height: 100%;
}

// 间距工具类
@for $i from 1 through 6 {
  .m-#{$i} {
    margin: #{$i * 4}px;
  }
  .mt-#{$i} {
    margin-top: #{$i * 4}px;
  }
  .mr-#{$i} {
    margin-right: #{$i * 4}px;
  }
  .mb-#{$i} {
    margin-bottom: #{$i * 4}px;
  }
  .ml-#{$i} {
    margin-left: #{$i * 4}px;
  }
  .p-#{$i} {
    padding: #{$i * 4}px;
  }
  .pt-#{$i} {
    padding-top: #{$i * 4}px;
  }
  .pr-#{$i} {
    padding-right: #{$i * 4}px;
  }
  .pb-#{$i} {
    padding-bottom: #{$i * 4}px;
  }
  .pl-#{$i} {
    padding-left: #{$i * 4}px;
  }
}
</style>