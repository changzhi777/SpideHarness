---
name: spide-search-fallback
description: >
  错误恢复搜索 — 当采集数据目标反复失败时，调用智谱 Web Search API 搜索 GitHub 
  寻找类似功能的代码进行学习，然后基于学习结果生成新的采集技能或适配器。
  当爬虫/采集任务失败且常规修复无效时使用此 skill。
---

# Spide Search Fallback — 错误恢复搜索

当采集数据目标反复失败、常规修复手段（spide-autofix 等）无效时，启动此 skill：搜索 GitHub 上类似功能的开源代码进行学习，然后生成新的采集技能。

## 触发条件

**必须满足以下条件之一才激活：**

1. 采集命令连续失败 **3 次以上**，且 spide-autofix 无法修复
2. 目标平台无现成适配器，需要从零开发采集能力
3. API/网页结构大幅变更，现有适配器已无法适配
4. 用户明确要求"搜索解决方案"或"去 GitHub 找找"

**不应触发的情况：**
- 首次失败（先用 spide-autofix 尝试修复）
- 简单的认证/Cookie 过期问题
- 网络连接问题（应运行 `opencli doctor`）

## 前提条件

```bash
# 确保 zai-sdk 已安装
pip install zai-sdk

# 确保 API Key 已配置（configs/llm.yaml 中的 zhipu.api_key）
```

## 核心流程

```
 ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
 │ 1. 收集上下文 │ ──▶ │ 2. 构造搜索   │ ──▶ │ 3. 搜索+分析  │ ──▶ │ 4. 生成新技能 │
 └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
   失败信息、目标        GitHub query         Web Search API        适配器/采集器
```

## Step 1: 收集失败上下文

在启动搜索前，整理以下信息：

| 信息项 | 说明 | 示例 |
|--------|------|------|
| 目标平台 | 要采集的网站/App | 小红书、抖音、B站 |
| 目标功能 | 要采集的具体数据 | 笔记详情、评论、用户主页 |
| 错误类型 | 失败的具体表现 | 403 Forbidden、空数据、DOM 变更 |
| 已尝试方法 | 已经做过哪些修复 | 修改选择器、更换 API 端点、重新登录 |
| 技术栈偏好 | 期望的实现方式 | Python + Playwright、TypeScript 适配器 |

## Step 2: 构造搜索 Query

根据失败上下文，构造精准的搜索查询词。遵循以下策略：

### 基础模板

```
{平台名} {功能} {语言} site:github.com
```

### 按场景的查询构造

| 场景 | 查询模板 | 示例 |
|------|---------|------|
| 寻找爬虫项目 | `{平台} crawler/spider/scraper python site:github.com` | `xiaohongshu crawler python site:github.com` |
| 寻找 API 封装 | `{平台} api sdk {语言} site:github.com` | `douyin api sdk python site:github.com` |
| 寻找特定功能 | `{平台} {功能} {语言} site:github.com` | `bilibili comments scraper python site:github.com` |
| 寻找解决方案 | `{错误描述} {技术} solution site:github.com` | `cloudflare bypass playwright python site:github.com` |
| 寻找适配器模式 | `{平台} adapter opencli site:github.com` | `zhihu adapter opencli site:github.com` |

### 查询优化规则

1. **优先加 `site:github.com`** — 限定搜索范围到代码仓库
2. **加语言限定** — 如 `python`、`typescript`、`node`
3. **用英文关键词** — 搜索效果优于中文（GitHub 内容以英文为主）
4. **多轮搜索** — 第一轮宽泛搜索找项目，第二轮精准搜索找具体实现
5. **每轮最多 3 次搜索** — 避免过度消耗 API 调用

## Step 3: 调用智谱 Web Search API 搜索并分析

### API 调用模板

```python
from zai import ZhipuAiClient

client = ZhipuAiClient(api_key="your-api-key")  # 从 configs/llm.yaml 读取

response = client.web_search.web_search(
    search_engine="search_pro",        # 高级版，多引擎协作，召回率高
    search_query=f"{platform} {feature} {language} site:github.com",
    count=15,                           # 返回 15 条结果
    content_size="high",                # 高摘要字数，获取更多代码片段
)
```

### 搜索参数策略

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `search_engine` | `search_pro` | 多引擎协作，空结果率低 |
| `count` | `15` | 首轮搜索多返回一些，扩大覆盖面 |
| `content_size` | `high` | 获取更长的摘要，可能包含代码片段 |
| `search_recency_filter` | `year` | 优先最近一年的项目，避免过时代码 |
| `search_domain_filter` | `github.com` | 限定 GitHub 域名 |

### 分析搜索结果

从返回结果中提取关键信息：

```python
for result in response.search_result:
    # 重点关注字段：
    # - title: 仓库名称
    # - link: GitHub 仓库 URL
    # - content: 摘要（可能包含代码片段）
    # - media: 来源
    # - refer: 引用标识
    print(f"[{result.refer}] {result.title}")
    print(f"  URL: {result.link}")
    print(f"  摘要: {result.content[:200]}")
```

### 筛选优先级

按以下优先级评估搜索结果：

1. **Star 数高的仓库** — 经过社区验证的可靠方案
2. **最近更新的仓库** — 代码维护活跃，适配最新接口
3. **包含具体实现的仓库** — 有完整爬虫/采集代码，非仅文档
4. **与目标平台直接匹配** — 专门针对目标平台的方案

### 深入分析

选定 2-3 个最相关的仓库后，使用 `mcp__fetch__fetch` 工具读取关键源码文件：

```
# 典型的仓库结构分析路径
1. README.md — 了解项目定位和使用方式
2. src/ 目录 — 核心实现代码
3. 爬虫/采集器主文件 — 关键逻辑
4. 配置文件 — API 端点、请求头模板
```

重点关注：
- **认证/反爬策略**：如何处理 Cookie、Token、签名
- **API 端点**：实际调用的 URL 和参数
- **数据解析**：响应结构解析方式
- **错误处理**：请求失败时的重试和降级策略

## Step 4: 生成新技能/适配器

基于学习结果，生成新的采集能力：

### 生成策略选择

| 学到的内容 | 生成方式 |
|-----------|---------|
| 发现了可用的 API 端点 | 生成 OpenCLI TS 适配器（参考 spide-oneshot 模板） |
| 发现了 Python 爬虫方案 | 生成 Python 采集脚本（集成到 src/spider/） |
| 发现了反爬绕过策略 | 生成新的策略模块（更新 spider 引擎） |
| 发现了完整的 SDK/库 | 集成到项目依赖（更新 pyproject.toml） |

### 生成新 OpenCLI 适配器

参考 [spide-oneshot](../spide-oneshot/SKILL.md) 的模板，将学到的 API 端点和认证方式写入 TS 适配器：

```typescript
// ~/.opencli/clis/<site>/<command>.ts
import { cli, Strategy } from '@jackwener/opencli/registry';

cli({
  site: '<site>',
  name: '<command>',
  description: '基于 GitHub 开源项目学习生成的适配器',
  domain: '<domain>',
  strategy: Strategy.COOKIE,  // 根据学到的认证方式选择
  browser: true,
  args: [{ name: 'limit', type: 'int', default: 20 }],
  columns: ['rank', 'title', 'value'],
  func: async (page, kwargs) => {
    // 基于学到的 API 端点和数据结构实现
  },
});
```

### 生成 Python 采集脚本

```python
# src/spider/custom/<platform>_<feature>.py
"""基于 GitHub 开源项目学习的采集脚本"""

import asyncio
import aiohttp

async def fetch_<feature>(session: aiohttp.ClientSession, **kwargs):
    """采集目标数据"""
    # 基于学到的 API 端点实现
    url = "https://api.example.com/endpoint"
    headers = {}  # 基于学到的认证方式
    async with session.get(url, headers=headers) as resp:
        data = await resp.json()
        return data
```

### 验证流程

生成新技能后，必须验证：

1. **代码可执行** — 无语法错误
2. **数据可获取** — 运行后能拿到目标数据
3. **输出结构化** — 数据格式符合预期

```bash
# 验证 OpenCLI 适配器
opencli browser verify <site>/<command>

# 验证 Python 脚本
python -m src.spider.custom.<platform>_<feature>
```

## 搜索预算

| 资源 | 限制 |
|------|------|
| 每次恢复任务的搜索轮次 | 最多 3 轮 |
| 每轮搜索查询数 | 1-2 个 |
| 每轮返回结果数 | 15 条 |
| 深入分析的仓库数 | 2-3 个 |
| 生成的适配器/脚本 | 1 个（最可靠的方案） |

## 完整工作流示例

```
场景：采集小红书用户笔记列表，连续失败 3 次

1. 收集上下文：
   - 目标：小红书用户笔记列表
   - 错误：API 签名验证失败，返回 403
   - 已尝试：更换选择器、重新登录、更换 User-Agent

2. 构造搜索：
   - 第 1 轮：search_pro, "xiaohongshu user notes scraper python site:github.com"
   - 发现 3 个相关项目

3. 搜索 + 分析：
   - 读取排名最高的仓库 README
   - 发现使用 playwright + cookie 认证方案
   - 读取核心采集代码，提取 API 端点和签名逻辑

4. 生成新技能：
   - 选择 TypeScript OpenCLI 适配器方案
   - 基于 cookie 策略编写适配器
   - 写入 ~/.opencli/clis/xiaohongshu/user-notes.ts
   - 验证：opencli browser verify xiaohongshu/user-notes
```

## 与其他 Skill 的协作

| Skill | 协作关系 |
|-------|---------|
| **spide-autofix** | 先用 autofix 尝试修复，失败 3 次后降级到本 skill |
| **spide-oneshot** | 搜索学习后，可能用 oneshot 流程生成适配器 |
| **spide-explorer** | 复杂场景可能需要 explorer 的完整探索流程 |
| **spide-browser** | 学习过程中可能需要 browser 查看实际网页结构 |
| **spide-search** | 补充搜索：除 GitHub 外也可搜索技术博客/教程 |

## 搜索引擎选择

| 搜索目的 | 推荐引擎 | 说明 |
|----------|---------|------|
| GitHub 代码搜索 | `search_pro` | 多引擎协作，覆盖面广 |
| 中文技术博客 | `search_pro_sogou` | 覆盖腾讯生态、知乎 |
| 垂直内容 | `search_pro_quark` | 精准触达特定领域 |
| 日常查询 | `search_std` | 性价比高 |

## 注意事项

- 搜索消耗 API 调用额度，遵循预算限制
- 学习开源代码时注意 License 兼容性
- 生成的适配器/脚本应标注来源和参考项目
- 不要直接复制粘贴大段代码，应理解核心逻辑后重新实现
- 如果搜索结果不足以解决问题，明确告知用户并建议替代方案
