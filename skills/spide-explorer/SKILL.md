---
name: spide-explorer
description: >
  适配器探索式开发 — 从零创建 OpenCLI 适配器，支持新网站/平台。
  涵盖 API 发现、认证策略选择、TS 适配器编写和测试验证。
  当用户要求为网站生成 CLI、探索网站 API 时使用。
---

# Spide Explorer — 适配器探索式开发完全指南

> 从零到发布：API 发现 → 认证策略 → 写适配器 → 测试验证。

## 前提条件

```bash
npm install -g @jackwener/opencli
opencli doctor
```

## 先选路径

| 情况 | 走这里 |
|------|--------|
| 只要为一个具体页面生成一个命令 | [spide-oneshot skill](../spide-oneshot/SKILL.md) |
| 想先让机器自动试一遍 | `opencli generate <url> [--goal <goal>]`，失败再回来 |
| 新站点 / 多个命令 / oneshot 卡住了 | 继续往下读本文档 |
| 产物要提 PR | 本文档 + `clis/<site>/` + `npm run build` |
| 只是本地私用，不提 PR | 本文档 + `~/.opencli/clis/<site>/` |

## 核心流程

```
 ┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌────────┐
 │ 1. 发现 API  │ ──▶ │ 2. 选择策略  │ ──▶ │ 3. 写适配器   │ ──▶ │ 4. 测试 │
 └─────────────┘     └─────────────┘     └──────────────┘     └────────┘
   browser explore     cascade             TS cli() API         verify
```

## 必须用浏览器探索

> **必须通过浏览器打开目标网站去探索！** 不要只靠静态分析。
> 很多 API 是**懒加载**的——字幕、评论、关注列表等深层数据只有点击后才触发。

### 浏览器探索工作流

| 步骤 | 命令 | 做什么 |
|------|------|--------|
| 0. 打开页面 | `opencli browser open <url>` | 导航到目标页面，开始捕获 |
| 1. 观察元素 | `opencli browser state` | 查看可交互元素（按钮/标签），带 `[N]` 索引 |
| 2. 首次抓包 | `opencli browser network` | 列出捕获的 JSON API 请求 |
| 3. 模拟交互 | `opencli browser click <N>` | 点击按钮触发懒加载 API |
| 4. 二次抓包 | `opencli browser network` | 找出新触发的 API |
| 5. 查看响应 | `opencli browser network --detail <N>` | 查看完整响应体 |
| 6. 验证 API | `opencli browser eval "fetch(...).then(r=>r.json())"` | 确认 API 可复现 |

### 实战示例：5 分钟实现「关注列表」适配器

```bash
opencli browser open https://space.bilibili.com/{uid}/fans/follow
opencli browser network
#   [0] GET 200 /x/relation/followings?vmid={uid}&pn=1&ps=24
opencli browser network --detail 0
# 确认数据结构：{ code: 0, data: { total: 1342, list: [{mid, uname, ...}] } }
opencli browser eval "fetch('/x/relation/followings?vmid=137702077&pn=1&ps=5', {credentials:'include'}).then(r=>r.json())"
# → 有数据，结论：Tier 2 Cookie，写 following.ts
```

## Step 1: 发现 API

### 高阶捷径（按优先级尝试）

1. **后缀爆破法 (`.json`)**：Reddit、雪球等，URL 加 `.json` 直接拿 REST 数据
2. **全局状态法 (`__INITIAL_STATE__`)**：SSR 站点（B站、小红书）首页数据挂载在 window 上
3. **主动交互触发法**：懒加载 API 需要点击按钮（"CC"、"展开全部"）才触发
4. **框架 Store 截断**：Vue + Pinia 站点，Store Action 代替你完成签名
5. **XHR/Fetch 拦截**：最后手段，用 `installInterceptor` 抓包

### 框架检测

```bash
opencli browser eval "(()=>{
  const vue3 = !!document.querySelector('#app')?.__vue_app__;
  const pinia = vue3 && !!document.querySelector('#app').__vue_app__.config.globalProperties.\$pinia;
  const react = !!window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
  return JSON.stringify({vue3, pinia, react});
})()"
```

## Step 2: 选择认证策略

```bash
opencli cascade https://api.example.com/hot   # 自动探测
```

### 策略决策树

```
fetch(url) 直接能拿到？
  → ✅ Tier 1: public（browser: false，~1s）
  → ❌ fetch(url, {credentials:'include'}) 带 Cookie 能拿到？
       → ✅ Tier 2: cookie（最常见）
       → ❌ localStorage 有 token，Bearer header 能拿到？
              → ✅ Tier 2.5: localStorage Bearer（现代 SaaS 主流）
              → ❌ 加 CSRF header 后能拿到？
                     → ✅ Tier 3: header（如 Twitter ct0 + Bearer）
                     → ❌ 网站有 Pinia/Vuex Store？
                            → ✅ Tier 4: intercept（Store Action + XHR 拦截）
                            → ❌ Tier 5: ui（UI 自动化，最后手段）
```

### 策略对比

| Tier | 策略 | 速度 | 适用场景 | 实例 |
|------|------|------|---------|------|
| 1 | `public` | ~1s | 公开 API，无需登录 | Hacker News, V2EX |
| 2 | `cookie` | ~7s | Cookie 认证即可 | Bilibili, Zhihu, Reddit |
| 2.5 | `localStorage Bearer` | ~7s | JWT 存 localStorage | Slock, Linear, Notion |
| 3 | `header` | ~7s | 需要 CSRF token 或 Bearer | Twitter GraphQL |
| 4 | `intercept` | ~10s | 请求有复杂签名 | 小红书 (Pinia + XHR) |
| 5 | `ui` | ~15s+ | 无 API，纯 DOM 解析 | 遗留网站 |

## Step 2.5: 复用现有适配器

```bash
ls clis/<site>/             # 看同站点已有什么
cat clis/<site>/feed.ts     # 读最相似的那个
```

改 3 处即可：`name`、API URL、字段映射。

## Step 3: 编写适配器

所有适配器统一使用 TypeScript `cli()` API，放入 `clis/<site>/<name>.ts` 即自动注册。

完整模板（Tier 1~4）、分页模式、错误处理规范 → **[adapter-templates.md](references/adapter-templates.md)**

级联请求、tap 调试、抗变更模式 → **[advanced-patterns.md](references/advanced-patterns.md)**

手动录制方案 → **[record-workflow.md](references/record-workflow.md)**

## Step 4: 测试

> **构建通过 ≠ 功能正常**。必须实际运行并确认输出。

```bash
# Repo 贡献：build 后直接运行
npm run build
opencli list | grep mysite                 # 确认注册
opencli mysite mycommand --limit 3 -v      # 实际运行

# 私人 adapter（~/.opencli/clis/）：一键验证
opencli browser verify <site>/<name>
```

**Done 标准**：命令运行后返回非空表格，且字段符合预期。

## 常见陷阱

| 陷阱 | 表现 | 解决方案 |
|------|------|---------|
| 缺少 `navigate` | `Target page context` 错误 | 在 evaluate 前加 `page.goto()` |
| 缺少 `strategy: public` | 公开 API 也启动浏览器 | 加 `strategy: Strategy.PUBLIC` + `browser: false` |
| 风控被拦截（伪 200） | JSON 里核心数据是空串 | 必须断言！返回 `{ error, help }` 提示重新登录 |
| SPA 返回 HTML | `fetch('/api/xxx')` 返回 `<!DOCTYPE html>` | API 在独立 domain，搜 JS bundle 找 baseURL |
| 文件写错目录 | `opencli list` 找不到命令 | Repo 放 `clis/<site>/` + build；私用放 `~/.opencli/clis/<site>/` |
| TS evaluate 格式 | `() => {}` 报错 | 必须用 IIFE：`(async () => { ... })()` |
| Cookie 过期 | 返回 401 / 空数据 | 在浏览器里重新登录目标站点 |

## 用 AI Agent 自动生成

```bash
# 一键：探索 → 分析 → 合成 → 注册
opencli generate https://www.example.com --goal "hot"

# 或分步：
opencli explore https://www.example.com --site mysite
opencli synthesize mysite
opencli verify mysite/hot --smoke
```
