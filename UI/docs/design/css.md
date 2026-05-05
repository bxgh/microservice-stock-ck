## 🎨 前端主题配置

### TailwindCSS 完整主题(与 Volume XI 对齐)

```typescript
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ==== 背景系(深色) ====
        'bg':       '#0a0906',    // 主背景
        'bg-elev':  '#13100b',    // 卡片
        'bg-deep':  '#1a1610',    // 嵌入
        'bg-inner': '#1f1a12',    // 最内层
        
        // ==== 文字(高对比度亮色) ====
        'ink':      '#f2ead8',    // 正文
        'ink-dim':  '#c9bfa8',    // 次要
        'ink-soft': '#8d8575',    // 弱文字
        'muted':    '#5c564a',    // 边框级
        
        // ==== 强调色 ====
        'accent':   '#d65d43',    // 朱砂红
        'accent-2': '#7fbba3',    // 青绿
        'gold':     '#e0b663',    // 金色
        'blue':     '#6fa8d0',    // 靛蓝
        'purple':   '#b88cd0',    // 紫
        
        // ==== 警报色 ====
        'alert-safe':     '#7fbba3',
        'alert-attention':'#e0b663',
        'alert-warning':  '#d65d43',
        'alert-critical': '#e87060',
        
        // ==== 层级色 ====
        'layer-1': '#d65d43',
        'layer-2': '#e0b663',
        'layer-3': '#7fbba3',
        'layer-4': '#6fa8d0',
        'layer-5': '#b88cd0',
        'layer-6': '#8d8575',
        
        // ==== 线条 ====
        'line':      '#332d22',
        'line-soft': '#241f17',
      },
      fontFamily: {
        'serif': ['"Noto Serif SC"', 'serif'],
        'display': ['"Cormorant Garamond"', 'serif'],
        'mono': ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config
```

### 常用组件样式模板

```tsx
// 统计卡
<div className="bg-bg-elev border border-line border-l-4 border-l-accent p-4">
  <div className="text-xs uppercase tracking-widest text-ink-soft">当前 CCI</div>
  <div className="text-2xl font-mono font-bold text-ink mt-1">1.24</div>
  <div className="text-xs text-ink-dim mt-1">二阶警戒</div>
</div>

// 警报徽章
<span className="inline-block px-2 py-1 text-xs font-mono tracking-wider 
                 bg-alert-warning/15 text-alert-warning border border-alert-warning">
  警戒
</span>
```

### 图表配色常量

```typescript
// src/lib/chartColors.ts
export const CHART_COLORS = {
  primary: '#d65d43',
  secondary: '#e0b663',
  tertiary: '#7fbba3',
  quaternary: '#6fa8d0',
  quinary: '#b88cd0',
  
  grid: '#332d22',
  axis: '#8d8575',
  label: '#c9bfa8',
  
  alert: {
    safe: '#7fbba3',
    attention: '#e0b663',
    warning: '#d65d43',
    critical: '#e87060',
  },
  
  layer: ['#d65d43', '#e0b663', '#7fbba3', '#6fa8d0', '#b88cd0', '#8d8575'],
};
```

---