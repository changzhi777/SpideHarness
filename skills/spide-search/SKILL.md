---
name: spide-search
description: >
  智能搜索路由 — 基于话题和场景，将查询路由到最佳的 opencli 搜索源。
  当用户需要搜索、查询、查找或研究信息时使用此 skill。
---

# Spide Search — 智能搜索路由器

根据话题和场景，将查询路由到最佳的 opencli 搜索源。此 skill 的核心目标不是记忆命令，而是先定位数据源，再通过 `opencli` 自己读取实时帮助，避免文档漂移。

## 前提条件

```bash
npm install -g @jackwener/opencli
opencli doctor
```

## 强制预检

每次使用前，必须先做下面两步：

- 运行 `opencli list -f yaml`
- 用 live registry 确认候选站点是否存在，并检查 `strategy`、`browser`、`domain`

选定站点后，必须再做下面两步：

- 运行 `opencli <site> -h` 查看该站点有哪些子命令
- 若已锁定某个子命令，再运行 `opencli <site> <command> -h` 查看参数、输出列、策略

不要在 skill 文档里硬编码参数或假设命令签名；以 `opencli ... -h` 的实时输出为准。

## 主路由规则

1. 当用户明确指定网站、平台或数据源时，直接使用对应网站。
2. 当用户没有指定网站时，优先只选择一个 AI 源：`grok`、`doubao`、`gemini` 三选一。
3. 当 AI 返回内容不足、缺少原始数据、需要权威佐证或需要垂直结果时，再补充 1-2 个专用源。

## 单题预算与频率限制

先建立一份站点调用台账。每次真正执行搜索命令后，立刻更新：

- `site`、`query`、`count`、`status`

计数规则：

- `opencli list -f yaml`、`opencli <site> -h`、`opencli <site> <command> -h` 属于预检，不计入搜索次数
- 一次真正的 `opencli <site> ...` 搜索执行，计为该站点 1 次调用
- 同站点因报错、超时、验证码等失败，也算 1 次调用

频率上限：

- AI 站点：同一题内每个 AI 站点最多调用 1 次
- 默认只选 1 个 AI 站点，不要把多个 AI 站点串成常规流程
- 非 AI 站点默认最多调用 2 次
- 非 AI 站点第 2 次调用必须有明确理由
- 非 AI 站点不进行第 3 次调用

## 查询结束汇报

每次查询结束后，回答末尾必须追加简短的搜索摘要：

```md
搜索摘要
- 网站：<site1> | 查询词：<term1> | 次数：<n>
- 网站：<site2> | 查询词：<term2>；<term3> | 次数：<n>
- 已跳过：<site3>，原因：达到频率上限
```

## AI 源选择

- **`grok`**：实时讨论、英文互联网舆论、Twitter/X 语境、热点追踪
- **`doubao`**：中文语境、字节抖音生态、生活方式内容、中文热点
- **`gemini`**：全球网页、英文资料、通用信息检索、背景综述

如果用户没有指定网站，默认先判断语言和语境，再从这三个里只选一个。

## AI 查询词建议

当使用 AI 源时，构造成"主题 + 目标 + 限定条件"的查询：

- `<主题> + <你要回答的问题>`
- `<主题> + <时间范围/地区/语言>`
- `<主题> + <平台或来源范围>`
- `<主题> + <输出要求>`

## 专用源补充时机

当出现以下任一情况时，再补充专用源：

- AI 给出的是摘要，但需要原始帖子/视频/商品结果
- AI 覆盖面不足，漏掉垂直站点信息
- 需要更高权威性或更强领域相关性
- 用户明确要求"从某个平台找"

单次查询通常控制在 1 个 AI 源 + 1 到 2 个专用源。

## 处理不可用的源

当站点不可用时：

- 不要因为单个源失败而中止整个搜索
- 记录：「已跳过：<site> 不可用」
- 回退到同类其他站点，或回退到一个 AI 源
- 始终以 `opencli list -f yaml` 与 `opencli <site> -h` 的实际结果为准

## 参考文件

根据需要读取对应文件：

- **`references/sources-ai.md`** — AI 默认源
- **`references/sources-tech.md`** — 技术 / 学术
- **`references/sources-social.md`** — 社交媒体
- **`references/sources-media.md`** — 媒体 / 娱乐
- **`references/sources-info.md`** — 资讯 / 知识
- **`references/sources-shopping.md`** — 购物
- **`references/sources-travel.md`** — 旅游
- **`references/sources-other.md`** — 其他垂直源

只读与当前查询相关的文件，无需全部加载。
