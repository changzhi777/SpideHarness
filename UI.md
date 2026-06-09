# text2mesh-ui 前端 UI 设计文档

## 1. 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 16.2.2 | 应用框架（静态导出） |
| React | 19.2.4 | UI 库 |
| TypeScript | 5 | 类型安全 |
| Tailwind CSS | v4 | 原子化样式（CSS 原生配置，无 tailwind.config） |
| shadcn/ui | base-nova | 组件库 |
| Zustand | v5 | 状态管理 |
| Three.js | v0.183 | 3D 渲染 |
| lucide-react | v1.7 | 图标库 |

---

## 2. 页面布局

### 2.1 主页 — 三栏仪表盘

全屏高度、不可滚动的单屏仪表盘布局。

```
┌──────────────────────────────────────────────────────────────────┐
│ HEADER (flex-shrink-0, border-b border-white/5, backdrop-blur)  │
│ [Logo + 标题]                         [头像] [状态] [GitHub链接] │
├──────────────────────────────────────────────────────────────────┤
│ ERROR BANNER (条件显示, flex-shrink-0)                            │
├──────────────────────────────────────────────────────────────────┤
│ MAIN CONTENT (flex-1, grid grid-cols-12 gap-3, min-h-0)         │
│                                                                  │
│  左栏 col-span-4      中栏 col-span-5        右栏 col-span-3    │
│ ┌──────────────────┐ ┌─────────────────────┐ ┌─────────────────┐│
│ │ GenerationPanel  │ │ TaskDetailPanel     │ │ HistoryPanel    ││
│ │ (文本/图片输入,   │ │ (3D 预览 +          │ │ (历史任务列表,   ││
│ │  参数设置, 提交)  │ │  任务元数据详情)     │ │  可滚动)        ││
│ └──────────────────┘ └─────────────────────┘ └─────────────────┘│
├──────────────────────────────────────────────────────────────────┤
│ FOOTER (flex-shrink-0, border-t border-white/5)                  │
│ "Powered by IoTchange V1.01"                                     │
└──────────────────────────────────────────────────────────────────┘
```

**背景装饰**（fixed, pointer-events-none）：
- 右上角：`w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl`
- 左下角：`w-96 h-96 bg-blue-500/10 rounded-full blur-3xl`
- 居中：`w-[800px] h-[800px] bg-emerald-500/5 rounded-full blur-3xl`

**主背景渐变**：`bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950`

### 2.2 头像游乐场 — 双栏布局

```
┌──────────────────────────────────────────────────────────────────┐
│ HEADER (含返回首页箭头, 模型加载说明)                             │
├────────────────────────────────────────────────────┬─────────────┤
│ 3D 场景 (flex-1)                                   │ 控制面板     │
│ <Canvas> 键盘控制 + 角色模型 + 轨道控制            │ w-72 border-l│
│                                                     │ - 模型加载   │
│                                                     │ - 骨骼面板   │
│                                                     │ - 录制控制   │
│                                                     │ - 动画面板   │
│                                                     │ - 骨骼控制   │
│                                                     │ - 纹理面板   │
├────────────────────────────────────────────────────┴─────────────┤
│ FOOTER                                                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. 主题配色

### 3.1 色彩体系

仅暗色模式（dark-only），所有颜色使用 **OKLCH** 色彩空间定义。

| 变量名 | OKLCH 值 | 近似 RGB | 用途 |
|--------|----------|---------|------|
| `--background` | `oklch(0.07 0.015 180)` | #0f181f | 页面背景 |
| `--foreground` | `oklch(0.985 0 0)` | #fafafa | 主文本 |
| `--card` | `oklch(0.12 0.02 160)` | #1a2530 | 卡片背景 |
| `--card-foreground` | `oklch(0.985 0 0)` | #fafafa | 卡片文本 |
| `--popover` | `oklch(0.12 0.02 160)` | #1a2530 | 弹出层背景 |
| `--popover-foreground` | `oklch(0.985 0 0)` | #fafafa | 弹出层文本 |
| `--primary` | `oklch(0.68 0.15 145)` | **#40BE7A** | 主要操作/强调 |
| `--primary-foreground` | `oklch(0.07 0 0)` | #0f0f0f | 主色上文本 |
| `--secondary` | `oklch(0.2 0.02 160)` | #2a3845 | 次要元素 |
| `--secondary-foreground` | `oklch(0.985 0 0)` | #fafafa | 次要文本 |
| `--muted` | `oklch(0.2 0.02 160)` | #2a3845 | 静默背景 |
| `--muted-foreground` | `oklch(0.65 0 0)` | #a0a0a0 | 静默文本 |
| `--accent` | `oklch(0.78 0.12 150)` | **#7ED4A6** | 辅助强调 |
| `--accent-foreground` | `oklch(0.07 0 0)` | #0f0f0f | 辅助色上文本 |
| `--destructive` | `oklch(0.55 0.2 25)` | #dc4545 | 危险/删除 |
| `--destructive-foreground` | `oklch(0.985 0 0)` | #fafafa | 危险色上文本 |
| `--border` | `oklch(0.25 0.02 160)` | #354555 | 边框 |
| `--input` | `oklch(0.25 0.02 160)` | #354555 | 输入框边框 |
| `--ring` | `oklch(0.68 0.15 145)` | #40BE7A | 焦点环 |

### 3.2 核心色彩速查

```
主色调（Emerald Green）:  #40BE7A  ← 按钮、活跃状态、进度条、焦点环
辅助色（Mint）:           #7ED4A6  ← 二级高亮、光晕效果
危险色（Red）:             #dc4545  ← 删除、错误
背景深色:                  #0f181f  ← 页面底色
卡片深色:                  #1a2530  ← 卡片、弹窗底色
边框色:                    #354555  ← 分割线、输入框
主文本:                    #fafafa  ← 标题、正文
次要文本:                  #a0a0a0  ← 说明、标签
```

### 3.3 组件级配色规则

| 场景 | 配色 |
|------|------|
| 主按钮 | `bg-primary text-primary-foreground` |
| 次要按钮 | `bg-secondary text-secondary-foreground` |
| 幽灵按钮 | `hover:bg-accent hover:text-accent-foreground` |
| 输入框 | `bg-transparent border-input` |
| 卡片 | `bg-card text-card-foreground` (无外边框或 `border-white/10`) |
| 标签（Badge） | `bg-{color}-500/20 text-{color}-400 border-{color}-500/30` |
| 成功状态 | `text-green-400 bg-green-500/10` |
| 错误状态 | `text-red-400 bg-red-500/10` |
| 处理中 | `text-yellow-400 bg-yellow-500/10` |
| 等待中 | `text-blue-400 bg-blue-500/10` |

---

## 4. 字体排版

### 4.1 字体族

| 字体 | CSS 变量 | 来源 |
|------|---------|------|
| Geist | `--font-geist-sans` → `--font-sans`, `--font-heading` | Google Fonts |
| Geist Mono | `--font-geist-mono` → `--font-mono` | Google Fonts |

HTML 根元素：`lang="zh-CN" class="antialiased"`

### 4.2 字号层级

| 级别 | Tailwind 类 | 场景 |
|------|------------|------|
| 页面标题 | `text-lg font-bold` | Header 中的产品名 |
| 卡片标题 | `text-base font-semibold` | CardTitle |
| 正文 | `text-sm` | 按钮文字、表体内容 |
| 辅助文本 | `text-xs` | 标签、说明文字 |
| 微型文本 | `text-[10px]` | 时间戳、进度标签 |
| 极小文本 | `text-[9px]` | 骨骼名称 |
| 等宽文本 | `font-mono` | 计时器、面数、Job ID |

---

## 5. 卡片与面板样式

### 5.1 通用卡片

```
玻璃态卡片:
  bg-card/60 border border-white/10 backdrop-blur-xl rounded-xl shadow-2xl

分割线:
  border-t border-white/5
  border-b border-white/5
```

### 5.2 GenerationPanel（左栏）

- **Tab 切换**：文生3D / 图生3D，`text-xs` 标签
- **输入区域**：Textarea（prompt）或 Image Dropzone
- **参数折叠区**：可展开的高级设置（模型版本、PBR、面数、格式等）
- **提交按钮**：`w-full bg-gradient-to-r from-emerald-500 to-emerald-600`，禁用态降低透明度
- **进度指示器**：阶段化进度条 + 模拟百分比 + 日志面板

### 5.3 TaskDetailPanel（中栏）

- **3D 预览区**：`SimpleModelViewer`（Google model-viewer 组件）或 React Three Fiber
- **空态**：SVG 3D 盒子图标 + 提示文字，`bg-muted/30 rounded-lg`
- **任务信息网格**：`grid grid-cols-2 gap-1.5`，标签+值配对
- **下载按钮**：`bg-gradient-to-r from-emerald-600 to-emerald-600`
- **删除按钮**：`bg-red-600/20 hover:bg-red-600/30 text-red-400 border-red-500/30`
- **全屏模式**：`bg-slate-900/95 backdrop-blur-sm` 覆盖层

### 5.4 HistoryPanel（右栏）

- **任务条目**：`rounded-lg border border-white/5 bg-white/5 hover:bg-white/10`
- **状态圆点**：蓝（pending）、黄（processing）、绿（completed）、红（failed）
- **滚动区域**：`overflow-y-auto`，内部可滚动

---

## 6. 动画效果

| 动画名 | CSS 实现 | 用途 |
|--------|---------|------|
| `pulse` | `animate-pulse` | 加载中骨架屏 |
| `spin` | `animate-spin` | 进度旋转图标 |
| `ping` | `animate-ping` | 录制指示红点 |
| `shimmer` | CSS keyframes | 加载态闪光 |
| `float` | CSS keyframes | 图标浮动效果 |
| `cube-rotate` | CSS keyframes | 3D 立方体旋转 |
| `accordion-down/up` | CSS keyframes | 折叠面板展开/收起 |

---

## 7. UI 基础组件（shadcn/ui）

### 7.1 Button

| 变体 | 样式特征 |
|------|---------|
| `default` | `bg-primary text-primary-foreground rounded-lg` |
| `outline` | `border border-input bg-transparent` |
| `secondary` | `bg-secondary text-secondary-foreground` |
| `ghost` | `hover:bg-accent` |
| `destructive` | `bg-destructive text-destructive-foreground` |
| `link` | `text-primary underline` |

**尺寸**：`default`(h-8), `xs`(h-6), `sm`(h-7), `lg`(h-9), `icon`(size-8), `icon-xs`(size-6), `icon-sm`(size-7), `icon-lg`(size-9)

### 7.2 Card

- 子组件：`CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`
- 基础样式：`rounded-xl border bg-card text-card-foreground shadow`

### 7.3 Badge

- 变体：`default`, `secondary`, `destructive`, `outline`
- 基础样式：`rounded-4xl h-5 px-2 text-xs font-medium`

### 7.4 Input / Textarea

- 基础：`h-8 rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-sm`
- 焦点：`focus-visible:border-ring focus-visible:ring-3`

### 7.5 其他

| 组件 | 用途 |
|------|------|
| Dialog | 模态对话框（AlertDialog 确认删除） |
| Tabs | 文生3D / 图生3D 切换 |
| Select | 模型版本、格式等下拉选择 |
| Slider | 面数滑块 |
| Progress | 进度条 |
| ScrollArea | 历史面板、日志面板滚动区域 |
| Skeleton | 加载骨架屏 |
| Checkbox | 布尔选项（PBR 开关等） |

---

## 8. 图标使用

图标库：**lucide-react**

| 类别 | 图标名 |
|------|--------|
| 导航 | `Hexagon`, `ExternalLink`, `ArrowLeft`, `Gamepad2` |
| 操作 | `Download`, `Upload`, `Trash2`, `X`, `RefreshCw`, `Maximize2`, `Minimize2` |
| 生成 | `Sparkles`, `Wand2`, `WandSparkles`, `ImageIcon`, `Loader2` |
| 状态 | `Zap`, `CheckCircle2`, `Circle`, `Square` |
| 设置 | `Settings2`, `Search`, `Palette` |
| 时间 | `Clock`, `Timer` |
| 历史 | `History`, `Eye`, `ChevronRight`, `ChevronDown`, `ChevronUp` |
| 3D | `Box`, `Shapes`, `Bone`, `Play`, `RotateCcw` |
| 媒体 | `Activity`, `FileBox` |

---

## 9. 状态管理

### 9.1 App Store（Zustand）

```typescript
interface AppState {
  currentTask: TaskResponse | null;      // 当前生成任务
  history: HistoryRecord[];               // 历史记录
  selectedTask: TaskResponse | null;      // 选中查看的任务
  isGenerating: boolean;                  // 正在生成
  isLoadingHistory: boolean;             // 正在加载历史
  error: string | null;                   // 全局错误
  progress: GenerationProgress;           // 进度信息
  progressMessages: ProgressMessage[];    // 进度日志
  generationStartTime: number | null;     // 计时起点
}
```

---

## 10. 设计原则总结

1. **暗色优先** — 全暗色背景，不提供亮色模式
2. **翡翠绿主色** — `#40BE7A` 贯穿所有交互元素
3. **玻璃态** — 卡片使用半透明 + `backdrop-blur`，营造层次感
4. **渐变背景** — 页面使用 `from-slate-950 via-slate-900` 三段渐变
5. **装饰光斑** — 固定定位的模糊圆形作为背景层次
6. **紧凑布局** — 三栏填充全屏，无空白滚动区域
7. **微交互** — 进度模拟、状态动画、hover 反馈
8. **一致性** — 统一的 `rounded-lg/xl` 圆角、`border-white/5~10` 透明边框
