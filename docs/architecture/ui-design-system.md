# UI Design System

## 🎨 Design Principles

### **Core Values**
- **Consistency**: Unified visual language across all components
- **Accessibility**: WCAG 2.1 AA compliance for all users
- **Responsiveness**: Mobile-first design approach
- **Performance**: Optimized for fast loading and smooth interactions
- **Maintainability**: Easy to update and scale

### **Design Tokens**

#### **Color System**
```scss
// Primary Colors
$primary-color: #409eff;
$primary-light: #79bbff;
$primary-dark: #337ecc;

// Secondary Colors
$success-color: #67c23a;
$warning-color: #e6a23c;
$danger-color: #f56c6c;
$info-color: #909399;

// Neutral Colors
$text-color-primary: #303133;
$text-color-regular: #606266;
$text-color-secondary: #909399;
$text-color-placeholder: #c0c4cc;

// Background Colors
$bg-color-white: #ffffff;
$bg-color-page: #f2f3f5;
$bg-color-overlay: rgba(255, 255, 255, 0.9);

// Border Colors
$border-color-light: #ebeef5;
$border-color-lighter: #f2f6fc;
$border-color-extra-light: #fafafa;
```

#### **Typography**
```scss
// Font Family
$font-family-primary: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
$font-family-mono: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;

// Font Sizes
$font-size-extra-large: 20px;
$font-size-large: 18px;
$font-size-medium: 16px;
$font-size-base: 14px;
$font-size-small: 13px;
$font-size-extra-small: 12px;

// Font Weights
$font-weight-primary: 500;
$font-weight-secondary: 400;

// Line Heights
$line-height-primary: 24px;
$line-height-secondary: 20px;
```

#### **Spacing System**
```scss
// Base spacing unit (4px)
$spacing-unit: 4px;

// Spacing scale
$spacing-1: $spacing-unit;      // 4px
$spacing-2: $spacing-unit * 2;  // 8px
$spacing-3: $spacing-unit * 3;  // 12px
$spacing-4: $spacing-unit * 4;  // 16px
$spacing-5: $spacing-unit * 5;  // 20px
$spacing-6: $spacing-unit * 6;  // 24px
$spacing-8: $spacing-unit * 8;  // 32px
$spacing-10: $spacing-unit * 10; // 40px
$spacing-12: $spacing-unit * 12; // 48px

// Semantic spacing
$spacing-xs: $spacing-1;
$spacing-sm: $spacing-2;
$spacing-md: $spacing-4;
$spacing-lg: $spacing-6;
$spacing-xl: $spacing-8;
$spacing-2xl: $spacing-10;
$spacing-3xl: $spacing-12;
```

#### **Border Radius**
```scss
$border-radius-base: 4px;
$border-radius-small: 2px;
$border-radius-large: 6px;
$border-radius-round: 20px;
$border-radius-circle: 50%;
```

#### **Shadows**
```scss
$box-shadow-light: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
$box-shadow-base: 0 2px 4px rgba(0, 0, 0, 0.12), 0 0 6px rgba(0, 0, 0, 0.04);
$box-shadow-dark: 0 2px 4px rgba(0, 0, 0, 0.12), 0 0 6px rgba(0, 0, 0, 0.12);
```

## 🧩 Component Guidelines

### **Button Variants**
```vue
<template>
  <!-- Primary Button -->
  <el-button type="primary" size="default">
    Primary Action
  </el-button>

  <!-- Secondary Button -->
  <el-button type="default" size="default">
    Secondary Action
  </el-button>

  <!-- Danger Button -->
  <el-button type="danger" size="default">
    Delete Action
  </el-button>

  <!-- Icon Button -->
  <el-button type="primary" :icon="Plus" circle />
</template>
```

### **Form Components**
```vue
<template>
  <el-form :model="form" :rules="rules" label-width="120px">
    <!-- Input Field -->
    <el-form-item label="Name" prop="name">
      <el-input
        v-model="form.name"
        placeholder="Enter your name"
        clearable
      />
    </el-form-item>

    <!-- Select Field -->
    <el-form-item label="Role" prop="role">
      <el-select v-model="form.role" placeholder="Select role">
        <el-option
          v-for="role in roles"
          :key="role.value"
          :label="role.label"
          :value="role.value"
        />
      </el-select>
    </el-form-item>

    <!-- Date Picker -->
    <el-form-item label="Date" prop="date">
      <el-date-picker
        v-model="form.date"
        type="date"
        placeholder="Select date"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
      />
    </el-form-item>
  </el-form>
</template>
```

### **Data Display**
```vue
<template>
  <!-- Table -->
  <el-table :data="tableData" stripe>
    <el-table-column prop="name" label="Name" />
    <el-table-column prop="status" label="Status">
      <template #default="{ row }">
        <el-tag :type="row.status === 'active' ? 'success' : 'info'">
          {{ row.status }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="Actions">
      <template #default="{ row }">
        <el-button type="primary" size="small" @click="editRow(row)">
          Edit
        </el-button>
      </template>
    </el-table-column>
  </el-table>

  <!-- Card -->
  <el-card shadow="hover" class="user-card">
    <template #header>
      <div class="card-header">
        <span>User Information</span>
        <el-button type="text" @click="handleEdit">Edit</el-button>
      </div>
    </template>
    <!-- Card content -->
  </el-card>
</template>
```

## 📱 Responsive Design

### **Breakpoints**
```scss
// Breakpoint variables
$breakpoint-xs: 480px;
$breakpoint-sm: 768px;
$breakpoint-md: 992px;
$breakpoint-lg: 1200px;
$breakpoint-xl: 1920px;

// Mixin for responsive design
@mixin respond-to($breakpoint) {
  @if $breakpoint == 'xs' {
    @media (max-width: $breakpoint-xs) { @content; }
  }
  @if $breakpoint == 'sm' {
    @media (max-width: $breakpoint-sm) { @content; }
  }
  @if $breakpoint == 'md' {
    @media (max-width: $breakpoint-md) { @content; }
  }
  @if $breakpoint == 'lg' {
    @media (max-width: $breakpoint-lg) { @content; }
  }
  @if $breakpoint == 'xl' {
    @media (max-width: $breakpoint-xl) { @content; }
  }
}
```

### **Grid System**
- Use Element Plus Grid (24-column system)
- Mobile-first approach
- Flexible gutters and spacing

### **Responsive Components**
```vue
<template>
  <div class="responsive-container">
    <el-row :gutter="20">
      <!-- Desktop: 3 columns, Mobile: 1 column -->
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <div class="grid-item">Item 1</div>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <div class="grid-item">Item 2</div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.grid-item {
  @include respond-to('sm') {
    margin-bottom: $spacing-md;
  }
}
</style>
```

## ♿ Accessibility Guidelines

### **Color Contrast**
- Text to background: Minimum 4.5:1
- Large text: Minimum 3:1
- Interactive elements: Minimum 3:1

### **Keyboard Navigation**
- All interactive elements keyboard accessible
- Visible focus indicators
- Logical tab order
- Skip links for navigation

### **Screen Reader Support**
- Semantic HTML elements
- ARIA labels and descriptions
- Alternative text for images
- Heading hierarchy

### **Accessibility Implementation**
```vue
<template>
  <!-- Accessible Button -->
  <el-button
    type="primary"
    :aria-label="buttonLabel"
    @click="handleClick"
  >
    Button Text
  </el-button>

  <!-- Accessible Form -->
  <el-form-item>
    <template #label>
      <label for="username">Username</label>
    </template>
    <el-input
      id="username"
      v-model="form.username"
      aria-describedby="username-help"
      aria-required="true"
    />
    <div id="username-help" class="sr-only">
      Enter your unique username for login
    </div>
  </el-form-item>

  <!-- Accessible Table -->
  <el-table>
    <el-table-column prop="name" header="Name" />
    <el-table-column prop="status" header="Status">
      <template #default="{ row }">
        <span
          :aria-label="`Status: ${row.status}`"
          :class="getStatusClass(row.status)"
        >
          {{ row.status }}
        </span>
      </template>
    </el-table-column>
  </el-table>
</template>
```

## 🎭 Animation & Transitions

### **Transition Guidelines**
- Keep animations under 300ms
- Use easing functions for natural motion
- Respect user's motion preferences
- Provide meaningful feedback

### **Common Animations**
```scss
// Fade transition
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// Slide transition
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from {
  transform: translateX(-100%);
}

.slide-leave-to {
  transform: translateX(100%);
}

// Respect motion preferences
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## 🎨 Icon System

### **Icon Usage**
- Use Element Plus Icons as primary set
- Consistent sizing: 16px, 20px, 24px
- Meaningful colors and semantic usage
- Accessibility with aria-labels

### **Icon Implementation**
```vue
<template>
  <!-- Standard icon -->
  <el-icon :size="20" color="#409eff">
    <Edit />
  </el-icon>

  <!-- Button with icon -->
  <el-button type="primary" :icon="Plus">
    Add Item
  </el-button>

  <!-- Semantic icon with accessibility -->
  <el-icon :size="16" :aria-label="isSuccess ? 'Success' : 'Error'">
    <Success v-if="isSuccess" />
    <Error v-else />
  </el-icon>
</template>
```

## 📐 Layout Standards

### **Container Standards**
- Max width containers for content
- Consistent spacing and padding
- Clear visual hierarchy
- Proper use of whitespace

### **Navigation**
- Clear navigation structure
- Breadcrumbs for hierarchy
- Search functionality
- Mobile-friendly menu

### **Page Layout**
```vue
<template>
  <div class="app-layout">
    <!-- Header -->
    <header class="app-header">
      <AppNavigation />
    </header>

    <!-- Main Content -->
    <main class="app-main">
      <div class="container">
        <router-view />
      </div>
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <AppFooter />
    </footer>
  </div>
</template>

<style scoped lang="scss">
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  padding: $spacing-lg 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 $spacing-md;
}
</style>
```

This design system ensures consistency, accessibility, and maintainability across all frontend applications while leveraging Element Plus as the base component library.