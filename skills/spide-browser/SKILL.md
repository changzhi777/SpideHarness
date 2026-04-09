---
name: spide-browser
description: >
  浏览器自动化 — 基于 OpenCLI 控制 Chrome 浏览器，支持导航、点击、输入、数据提取。
  复用已有登录会话，无需密码。当用户需要浏览网页、提取网页数据、自动化浏览器操作时使用。
---

# Spide Browser — 浏览器自动化

基于 [OpenCLI](https://github.com/jackwener/opencli) 的浏览器自动化能力，控制 Chrome 逐步操作。复用已有登录会话 — 无需密码。

## 前提条件

```bash
# 1. 安装 OpenCLI（首次使用）
npm install -g @jackwener/opencli

# 2. 验证环境
opencli doctor    # 检查扩展 + 守护进程连通性
```

需要：Chrome 运行中 + OpenCLI Browser Bridge 扩展已安装。

> 安装检查已集成到 `spide init` / `spide doctor` 流程中。

## 关键规则

1. **始终用 `state` 检查页面，绝不用 `screenshot`** — `state` 返回结构化 DOM 带 `[N]` 元素索引，瞬间完成且零 token 消耗。`screenshot` 需要视觉处理且慢。仅当用户明确要求保存视觉截图时使用。
2. **始终用 `click`/`type`/`select` 交互，绝不用 `eval` 点击或输入** — `eval "el.click()"` 绕过 scrollIntoView 和 CDP 点击管线，会导致屏幕外元素操作失败。用 `state` 找到 `[N]` 索引，然后 `click <N>`。
3. **用 `get value` 验证输入，不用截图** — `type` 后运行 `get value <index>` 确认。
4. **每次页面变更后都运行 `state`** — 在 `open`、`click`（链接）、`scroll` 后，始终运行 `state` 查看新元素和索引。绝不猜测索引。
5. **积极用 `&&` 链接命令** — 合并 `open + state`、多个 `type`、以及 `type + get value` 为单次 `&&` 链。每次工具调用都有开销；链接能减少开销。
6. **`eval` 仅用于只读** — 仅用 `eval` 提取数据（`JSON.stringify(...)`），绝不用于点击、输入或导航。始终用 IIFE 包裹避免变量冲突：`eval "(function(){ const x = ...; return JSON.stringify(x); })()"`。
7. **最小化工具调用总数** — 行动前先规划序列。好的任务完成使用 3-5 次调用，而非 15-20 次。合并 `open + state` 为一次调用。合并 `type + type + click` 为一次调用。仅在需要发现新索引时才单独运行 `state`。
8. **优先用 `network` 发现 API** — 大多数站点有 JSON API。基于 API 的适配器比 DOM 抓取更可靠。

## 命令开销指南

| 开销 | 命令 | 使用时机 |
|------|------|---------|
| **免费且瞬间** | `state`, `get *`, `eval`, `network`, `scroll`, `keys` | 默认使用 |
| **免费但改变页面** | `open`, `click`, `type`, `select`, `back` | 交互后运行 `state` |
| **昂贵（视觉 token）** | `screenshot` | 仅当用户需要保存图片 |

## 操作链接规则

命令可用 `&&` 链接。浏览器通过守护进程持久化，链接是安全的。

**始终尽量链接** — 更少的工具调用 = 更快的完成：

```bash
# 好：open + 检查在一次调用中（节省 1 次往返）
opencli browser open https://example.com && opencli browser state

# 好：一次调用填表（节省 2 次往返）
opencli browser type 3 "hello" && opencli browser type 4 "world" && opencli browser click 7

# 好：输入 + 验证在一次调用中
opencli browser type 5 "test@example.com" && opencli browser get value 5

# 好：点击 + 等待 + 状态在一次调用中（用于改变页面的点击）
opencli browser click 12 && opencli browser wait time 1 && opencli browser state
```

**页面变更操作始终放在链末**（后续命令看到的是旧索引）：
- `open <url>`, `back`, `click <link/button that navigates>`

**规则**：已知索引时链接。需要先发现索引时才单独运行 `state`。

## 核心工作流

1. **导航**：`opencli browser open <url>`
2. **检查**：`opencli browser state` → 带 `[N]` 索引的元素
3. **交互**：使用索引 — `click`, `type`, `select`, `keys`
4. **等待**（如需）：`opencli browser wait selector ".loaded"` 或 `wait text "Success"`
5. **验证**：`opencli browser state` 或 `opencli browser get value <N>`
6. **重复**：命令间浏览器保持打开
7. **保存**：将 TS 适配器写入 `~/.opencli/clis/<site>/<command>.ts`

## 命令参考

### 导航

```bash
opencli browser open <url>              # 打开 URL（改变页面）
opencli browser back                    # 后退（改变页面）
opencli browser scroll down             # 滚动（up/down，--amount N）
opencli browser scroll up --amount 1000
```

### 检查（免费且瞬间）

```bash
opencli browser state                   # 结构化 DOM 带 [N] 索引 — 主要工具
opencli browser screenshot [path.png]   # 保存视觉到文件 — 仅用于用户交付物
```

### 获取（免费且瞬间）

```bash
opencli browser get title               # 页面标题
opencli browser get url                 # 当前 URL
opencli browser get text <index>        # 元素文本内容
opencli browser get value <index>       # 输入框/textarea 值（用于 type 后验证）
opencli browser get html                # 完整页面 HTML
opencli browser get html --selector "h1" # 限定范围 HTML
opencli browser get attributes <index>  # 元素属性
```

### 交互

```bash
opencli browser click <index>           # 点击元素 [N]
opencli browser type <index> "text"     # 在元素 [N] 中输入
opencli browser select <index> "option" # 下拉选择
opencli browser keys "Enter"            # 按键（Enter, Escape, Tab, Control+a）
```

### 等待

```bash
opencli browser wait time 3                       # 等待 N 秒（固定延迟）
opencli browser wait selector ".loaded"            # 等待直到元素出现在 DOM
opencli browser wait selector ".spinner" --timeout 5000  # 带超时（默认 30s）
opencli browser wait text "Success"                # 等待直到文本出现
```

**何时等待**：在 SPA 上 `open` 后、触发异步加载的 `click` 后、动态渲染内容上的 `eval` 前。

### 提取（免费且瞬间，只读）

```bash
opencli browser eval "document.title"
opencli browser eval "JSON.stringify([...document.querySelectorAll('h2')].map(e => e.textContent))"

# 重要：复杂逻辑用 IIFE 包裹避免 "already declared" 错误
opencli browser eval "(function(){ const items = [...document.querySelectorAll('.item')]; return JSON.stringify(items.map(e => e.textContent)); })()"
```

**选择器安全**：始终使用备用选择器 — `querySelector` 未匹配时返回 `null`：

```bash
# 好：带 || 或 ?. 的备用
opencli browser eval "(document.querySelector('.title') || document.querySelector('h1') || {textContent:''}).textContent"
opencli browser eval "document.querySelector('.title')?.textContent ?? 'not found'"
```

### 网络（API 发现）

```bash
opencli browser network                  # 显示捕获的 API 请求（open 后自动捕获）
opencli browser network --detail 3       # 显示请求 #3 的完整响应体
opencli browser network --all            # 包含静态资源
```

### 沉淀（保存为 CLI）

```bash
opencli browser init hn/top              # 在 ~/.opencli/clis/hn/top.ts 生成适配器脚手架
opencli browser verify hn/top            # 测试适配器
```

### 会话

```bash
opencli browser close                   # 关闭自动化窗口
```

## 示例：提取 HN 故事

```bash
opencli browser open https://news.ycombinator.com
opencli browser state                   # 看到 [1] a "Story 1", [2] a "Story 2"...
opencli browser eval "JSON.stringify([...document.querySelectorAll('.titleline a')].slice(0,5).map(a => ({title: a.textContent, url: a.href})))"
opencli browser close
```

## 策略指南

| 策略 | 适用场景 | browser: |
|------|---------|----------|
| `Strategy.PUBLIC` | 公开 API，无需认证 | `false` |
| `Strategy.COOKIE` | 需要 Cookie 认证 | `true` |
| `Strategy.UI` | 直接 DOM 交互 | `true` |

**始终优先 API 而非 UI** — 如果浏览时发现了 API，直接用 `fetch()`。

## 常见问题

| 错误 | 修复 |
|------|------|
| "Browser not connected" | 运行 `opencli doctor` |
| "attach failed: chrome-extension://" | 临时禁用 1Password |
| 元素未找到 | `opencli browser scroll down && opencli browser state` |
| 页面变更后索引过时 | 再次运行 `opencli browser state` 获取新索引 |

## 相关 Skills

- **spide-explorer** — 适配器探索式开发（API 发现、认证策略、编写适配器）
- **spide-oneshot** — 从 URL 快速生成单个命令
- **spide-autofix** — 命令失败时自动修复适配器
- **spide-search** — 智能搜索路由（AI + 多源）
