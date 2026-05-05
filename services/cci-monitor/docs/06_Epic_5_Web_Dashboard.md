## Epic 5: Web 仪表盘

### Epic 目标

构建**生产级 Web 仪表盘**。与 Streamlit 不同,这是完整的 React SPA,样式和交互更精细。

### Stories

---

#### Story 5.1: 前端项目初始化

**技术选型说明:**

使用 **Vite + React 18 + TypeScript + TailwindCSS + shadcn/ui**,理由:
- Vite 开发体验最佳,构建快
- TailwindCSS 实现 Volume XI 配色最直接
- shadcn/ui 组件质量高且可定制
- TypeScript 降低 bug 率

**初始化步骤:**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# shadcn-ui
npx shadcn-ui@latest init

# 依赖
npm install react-router-dom zustand @tanstack/react-query axios recharts d3 date-fns
npm install -D @types/d3
```

**TailwindCSS 主题配置(对齐 Volume XI 深色风格):**

```typescript
// tailwind.config.ts
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // === 深色背景 ===
        'bg':       '#0a0906',
        'bg-elev':  '#13100b',
        'bg-deep':  '#1a1610',
        'bg-inner': '#1f1a12',
        
        // === 文字 ===
        'ink':      '#f2ead8',
        'ink-dim':  '#c9bfa8',
        'ink-soft': '#8d8575',
        
        // === 强调色 ===
        'accent':   '#d65d43',
        'gold':     '#e0b663',
        'green':    '#7fbba3',
        'blue':     '#6fa8d0',
        'purple':   '#b88cd0',
        
        // === 警报色 ===
        'alert-safe':     '#7fbba3',
        'alert-attention':'#e0b663',
        'alert-warning':  '#d65d43',
        'alert-critical': '#e87060',
        
        // === 层级色 ===
        'layer-1': '#d65d43',
        'layer-2': '#e0b663',
        'layer-3': '#7fbba3',
        'layer-4': '#6fa8d0',
        'layer-5': '#b88cd0',
        'layer-6': '#8d8575',
        
        // === 线条 ===
        'line':      '#332d22',
        'line-soft': '#241f17',
      },
      fontFamily: {
        'serif': ['"Noto Serif SC"', 'serif'],
        'display': ['"Cormorant Garamond"', 'serif'],
        'mono': ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
};
```

**验收标准:**
- [ ] `npm run dev` 启动开发服务器
- [ ] TailwindCSS 主题色与 Volume XI 对齐
- [ ] 有基础的路由框架(Dashboard / Layers / Backtest / Settings)

**预计工时:** 4 小时

---

#### Story 5.2: API 客户端与数据层

**技术实现:**

```typescript
// src/services/api.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
});

// 响应拦截
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export interface CCIResponse {
  date: string;
  layer_id: number;
  cci: number;
  alpha: number;
  beta: number;
  gamma: number;
  delta: number;
  alert_level: number;
  alert_label: string;
  market_rho: number;
  resonant_rho: number | null;
  deep_rho: number | null;
  delta_rho: number | null;
  up_down_ratio: number | null;
}

export const api = {
  getLatestCCI: (layer: number = 1): Promise<CCIResponse> =>
    apiClient.get(`/api/v1/cci/latest?layer=${layer}`),
  
  getCCIHistory: (layer: number, start: string, end: string): Promise<CCIResponse[]> =>
    apiClient.get(`/api/v1/cci/history`, { params: { layer, start, end } }),
  
  getAllLayers: (): Promise<CCIResponse[]> =>
    apiClient.get(`/api/v1/layers/latest`),
  
  getBacktestResult: (): Promise<BacktestResponse> =>
    apiClient.get(`/api/v1/backtest/latest`),
  
  getSystemHealth: (): Promise<HealthResponse> =>
    apiClient.get(`/api/v1/system/health`),
};
```

**使用 React Query 管理数据:**

```typescript
// src/hooks/useCCI.ts
import { useQuery } from '@tanstack/react-query';

export function useLatestCCI(layer: number = 1) {
  return useQuery({
    queryKey: ['cci', 'latest', layer],
    queryFn: () => api.getLatestCCI(layer),
    staleTime: 60_000,  // 1 分钟内不重复请求
    refetchInterval: 5 * 60_000,  // 每 5 分钟刷新
  });
}
```

**验收标准:**
- [ ] 所有 API 响应有完整 TypeScript 类型
- [ ] 使用 React Query 缓存和自动刷新
- [ ] 错误状态有统一处理

**预计工时:** 3 小时

---

#### Story 5.3: CCI 仪表盘半圆图

**技术实现:**

使用 recharts RadialBarChart 或自定义 SVG。推荐自定义 SVG 以完全控制视觉。

```typescript
// src/components/charts/CCIGauge.tsx
interface Props {
  cci: number;
  alertLevel: number;
  size?: number;
}

export function CCIGauge({ cci, alertLevel, size = 280 }: Props) {
  // 映射 CCI 值到角度 (0 → -90°, 2 → 90°)
  const angle = Math.min(Math.max(cci / 2, 0), 1) * 180 - 90;
  const color = getAlertColor(alertLevel);
  
  return (
    <svg viewBox="0 0 280 200" className="w-full">
      {/* 渐变定义 */}
      <defs>
        <linearGradient id="gaugeGrad">
          <stop offset="0%" stopColor="#7fbba3" />
          <stop offset="50%" stopColor="#e0b663" />
          <stop offset="80%" stopColor="#d65d43" />
          <stop offset="100%" stopColor="#e87060" />
        </linearGradient>
      </defs>
      
      {/* 背景弧 */}
      <path
        d="M 40 160 A 100 100 0 0 1 240 160"
        fill="none"
        stroke="url(#gaugeGrad)"
        strokeWidth="20"
        strokeLinecap="round"
      />
      
      {/* 刻度标签 */}
      {/* ... */}
      
      {/* 指针 */}
      <g transform={`rotate(${angle} 140 160)`}>
        <line
          x1="140" y1="160"
          x2="140" y2="70"
          stroke="#f2ead8"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="140" cy="160" r="10" fill={color} stroke="#f2ead8" strokeWidth="2" />
      </g>
      
      {/* 中心标签 */}
      <text x="140" y="190" textAnchor="middle" className="font-display italic" fill={color}>
        CCI {cci.toFixed(2)}
      </text>
    </svg>
  );
}
```

**验收标准:**
- [ ] 与 Volume XI 文档中的仪表盘视觉一致
- [ ] 指针平滑动画过渡
- [ ] 响应式(适配不同尺寸)

**预计工时:** 4 小时

---

#### Story 5.4: 主仪表盘页面

**页面布局:**

```
┌─────────────────────────────────────────────────┐
│  Sidebar     │   TopBar (刷新按钮 · 当前时间)     │
│  - Dashboard │─────────────────────────────────  │
│  - Layers    │                                    │
│  - Backtest  │   ┌──────────┐  ┌──────────────┐  │
│  - Settings  │   │          │  │ CCI 历史曲线  │  │
│              │   │  CCI 仪表 │  │ 60 天         │  │
│              │   │          │  │              │  │
│              │   └──────────┘  └──────────────┘  │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │    四分量条形图              │ │
│              │   │    α · β · γ · δ            │ │
│              │   └──────────────────────────────┘ │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │  ρ̄ 时间序列 + 形态ABC标记   │ │
│              │   └──────────────────────────────┘ │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │  六层 CCI 热力图             │ │
│              │   └──────────────────────────────┘ │
│              │                                    │
│              │   ┌──────────────────────────────┐ │
│              │   │  最近预警列表                │ │
│              │   └──────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**验收标准:**
- [ ] 所有图表数据来自 API
- [ ] 响应式,移动端可用
- [ ] 加载时有 skeleton 占位
- [ ] 页面首屏加载 < 2 秒

**预计工时:** 8-10 小时

---

#### Story 5.5: 分层监测页面 (6h)
#### Story 5.6: 回测页面 (6h)
#### Story 5.7: 设置页面 (3h)

---

