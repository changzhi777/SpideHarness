---
name: spide-autofix
description: >
  适配器自动修复 — 当 opencli 命令因网站 DOM/API 变更而失败时，自动诊断、修复适配器并重试。
  当 opencli 命令失败时使用此 skill。
---

# Spide AutoFix — 适配器自动修复

当 `opencli` 命令因网站 DOM、API 或响应结构变更而失败时，**自动诊断、修复适配器并重试** — 不要只是报告错误。

## 安全边界

**开始任何修复前，检查这些硬性停止条件：**

- **`AUTH_REQUIRED`**（退出码 77）— **停止。** 不要修改代码。告诉用户在 Chrome 中登录目标站点。
- **`BROWSER_CONNECT`**（退出码 69）— **停止。** 不要修改代码。告诉用户运行 `opencli doctor`。
- **验证码 / 频率限制** — **停止。** 不是适配器问题。

**范围约束：**
- **仅修改 `RepairContext.adapter.sourcePath` 处的文件** — 这是权威适配器位置（可能是仓库中的 `clis/<site>/` 或 npm 安装的 `~/.opencli/clis/<site>/`）
- **绝不修改** `src/`、`extension/`、`tests/`、`package.json` 或 `tsconfig.json`

**重试预算：** 每次故障最多 **3 轮修复**。如果 3 轮 诊断→修复→重试 仍未解决，停止并报告已尝试的操作。

## 前提条件

```bash
opencli doctor    # 验证扩展 + 守护进程连通性
```

## 何时使用此 Skill

当 `opencli <site> <command>` 因可修复错误而失败时使用：

- **SELECTOR** — 元素未找到（DOM 变更）
- **EMPTY_RESULT** — 无数据返回（API 响应变更）
- **API_ERROR** / **NETWORK** — 端点移动或中断
- **PAGE_CHANGED** — 页面结构不再匹配
- **COMMAND_EXEC** — 适配器逻辑中的运行时错误
- **TIMEOUT** — 页面加载方式改变，适配器等待了错误的内容

## 进入修复前："空结果" ≠ "损坏"

`EMPTY_RESULT` — 有时结构有效的 `SELECTOR` 返回空 — 通常**不是适配器 bug**。平台主动在反爬策略下降级结果，站点返回的"未找到"响应并不意味着内容真的缺失。**在**提交修复之前排除这种情况：

- **用替代查询或入口点重试。** 如果 `opencli xiaohongshu search "X"` 返回 0 但 `opencli xiaohongshu search "X 攻略"` 返回 20，适配器没问题 — 平台在塑造第一个查询的结果。
- **在普通 Chrome 标签页中抽查。** 如果数据在用户自己的浏览器中可见但适配器返回空，问题通常是认证状态、频率限制或软封 — 不是代码 bug。修复方式是 `opencli doctor` / 重新登录，而不是编辑源码。
- **查找软 404。** 小红书/微博/抖音等站点在项目隐藏或删除时返回 HTTP 200 和空载荷而非真正的 404。快照看起来结构正确。2-3 秒后重试通常能区分"暂时隐藏"和"真的消失"。
- **搜索"0 结果"是一个答案。** 如果适配器成功到达搜索端点，得到 HTTP 200，平台返回 `results: []`，这是一个有效答案 — 向用户报告"此查询无匹配"，而不是修补适配器。

仅当空结果/选择器缺失结果在**重试和替代入口点中可复现**时才进入 Step 1。否则你是在修补一个正常工作的适配器来追踪噪声，修补后的版本会破坏下一个可用路径。

## Step 1：收集诊断上下文

启用诊断模式运行失败的命令：

```bash
OPENCLI_DIAGNOSTIC=1 opencli <site> <command> [args...] 2>diagnostic.json
```

这会在 stderr 的 `___OPENCLI_DIAGNOSTIC___` 标记之间输出 `RepairContext` JSON：

```json
{
  "error": {
    "code": "SELECTOR",
    "message": "Could not find element: .old-selector",
    "hint": "The page UI may have changed."
  },
  "adapter": {
    "site": "example",
    "command": "example/search",
    "sourcePath": "/path/to/clis/example/search.ts",
    "source": "// 完整适配器源代码"
  },
  "page": {
    "url": "https://example.com/search",
    "snapshot": "// 带 [N] 索引的 DOM 快照",
    "networkRequests": [],
    "consoleErrors": []
  },
  "timestamp": "2025-01-01T00:00:00.000Z"
}
```

## Step 2：分析故障

读取诊断上下文和适配器源码，分类根因：

| 错误码 | 可能原因 | 修复策略 |
|--------|---------|---------|
| SELECTOR | DOM 重构，class/id 重命名 | 探索当前 DOM → 找到新选择器 |
| EMPTY_RESULT | API 响应结构变更，或数据移位 | 检查网络 → 找到新响应路径 |
| API_ERROR | 端点 URL 变更，需要新参数 | 通过网络拦截发现新 API |
| AUTH_REQUIRED | 登录流程变更，Cookie 过期 | **停止** — 让用户登录，不要修改代码 |
| TIMEOUT | 页面加载方式改变，spinner/懒加载 | 添加/更新等待条件 |
| PAGE_CHANGED | 重大改版 | 可能需要完整重写适配器 |

## Step 3：探索当前网站

用 `opencli browser` 检查实时网站。**绝不使用损坏的适配器** — 它只会再次失败。

```bash
# DOM 变更（SELECTOR 错误）
opencli browser open https://example.com/target-page && opencli browser state

# API 变更（API_ERROR, EMPTY_RESULT）
opencli browser open https://example.com/target-page && opencli browser state
opencli browser click <N> && opencli browser network
opencli browser network --detail <index>
```

## Step 4：修补适配器

读取 `RepairContext.adapter.sourcePath` 处的适配器源文件并进行针对性修复。

### 修补规则

1. **做最小变更** — 只修复损坏的部分，不要重构
2. **保持相同的输出结构** — `columns` 和返回格式必须保持兼容
3. **优先 API 而非 DOM 抓取** — 如果探索中发现了 JSON API，切换到它
4. **仅使用 `@jackwener/opencli/*` 导入** — 绝不添加第三方包导入
5. **修补后测试** — 再次运行命令验证

### 常见修复

**选择器更新：**
```typescript
// 前：page.evaluate('document.querySelector(".old-class")...')
// 后：page.evaluate('document.querySelector(".new-class")...')
```

**API 端点变更：**
```typescript
// 前：const resp = await page.evaluate(`fetch('/api/v1/old-endpoint')...`)
// 后：const resp = await page.evaluate(`fetch('/api/v2/new-endpoint')...`)
```

**响应结构变更：**
```typescript
// 前：const items = data.results
// 后：const items = data.data.items
```

**等待条件更新：**
```typescript
// 前：await page.waitForSelector('.loading-spinner', { hidden: true })
// 后：await page.waitForSelector('[data-loaded="true"]')
```

## Step 5：验证修复

```bash
# 正常运行命令（不带诊断模式）
opencli <site> <command> [args...]
```

如果仍然失败，回到 Step 1 收集新的诊断信息。你有 **3 轮修复**预算。如果同一错误在修复后持续存在，尝试不同方法。3 轮后停止并报告已尝试的操作。

## 何时停止

**硬性停止（不要修改代码）：**
- **AUTH_REQUIRED / BROWSER_CONNECT** — 环境问题，不是适配器 bug
- **站点需要验证码** — 无法自动化
- **频率限制 / IP 封禁** — 不是适配器问题

**软性停止（尝试后报告）：**
- **3 轮修复用尽** — 停止，报告已尝试和失败的内容
- **功能完全移除** — 数据已不存在
- **重大改版** — 需要通过 spide-explorer 完整重写适配器
