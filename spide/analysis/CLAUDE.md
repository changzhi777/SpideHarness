# AI 分析模块

> [根目录](../../CLAUDE.md) > [spide](../) > **analysis**

## 职责

基于 LLM 的智能分析能力，包括内容摘要、趋势分析、智能采集策略、词云生成、跨平台关联分析和标题相似度计算。

## 文件清单（5 个文件，含 `__init__.py`）

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块初始化 |
| `summarizer.py` | ContentSummarizer + TrendAnalyzer + SmartCrawlStrategy（含 `_call_llm_json` + `_try_repair_truncated_json` 工具函数）|
| `wordcloud_generator.py` | WordCloudGenerator — jieba 分词 + wordcloud 生成 |
| `cross_platform.py` | CrossPlatformAnalyzer — LLM 语义聚类 + 跨平台去重 |
| `title_similarity.py` | jieba Jaccard + Levenshtein 编辑距离相似度 |

## 核心类

### ContentSummarizer
```python
from spide.analysis.summarizer import ContentSummarizer

summarizer = ContentSummarizer(llm_client)
result = await summarizer.summarize(title="标题", content="正文")
# → {"summary": "...", "keywords": [...], "category": "tech"}

keywords = await summarizer.extract_keywords(title="...", content="...")
sentiment = await summarizer.analyze_sentiment(comments=["好文", "垃圾"])
```

### TrendAnalyzer
```python
analyzer = TrendAnalyzer(llm_client)
result = await analyzer.analyze(current_topics, previous_topics)
# → {"analysis": "...", "top_categories": [...], "hot_domains": [...]}
```

### SmartCrawlStrategy
```python
strategist = SmartCrawlStrategy(llm_client)
result = await strategist.recommend(topics_data)
# → {"analysis": "...", "search_keywords": [...], "recommended_sources": [...]}
```

### WordCloudGenerator
```python
from spide.analysis.wordcloud_generator import WordCloudGenerator

gen = WordCloudGenerator(output_dir="data/wordcloud", max_words=200)
filepath = await gen.generate_from_texts(titles, filename="weibo", title="微博热搜")
freq = await gen.get_top_keywords(titles, text_field="")
```

特性：jieba 中文分词 + 停用词过滤 + matplotlib wordcloud。

### CrossPlatformAnalyzer
```python
analyzer = CrossPlatformAnalyzer(llm_client)
clusters = await analyzer.analyze({"weibo": topics1, "zhihu": topics2})
# → [TopicCluster(cluster_name, cluster_keywords, platform_sources, ...)]
```

### title_similarity
```python
from spide.analysis.title_similarity import is_similar, jaccard_similarity, levenshtein_similarity

similar = is_similar("标题A", "标题B", threshold=0.6)
jacc = jaccard_similarity("标题A", "标题B")  # 0.0 ~ 1.0
lev = levenshtein_similarity("标题A", "标题B")  # 0.0 ~ 1.0
```

算法：jieba 分词 → 集合 Jaccard + 字符级 Levenshtein 编辑距离。

## 依赖

- `spide.llm` (LLMClient) — summarizer/trend/strategy/cross_platform
- `spide.storage.models` — HotTopic, TopicCluster
- jieba — 中文分词
- wordcloud + matplotlib — 词云生成
- python-Levenshtein — 编辑距离（可选加速）

## 设计原则

- **KISS** — 每个类职责单一，可独立使用
- **可降级** — LLM 调用失败时返回降级结果（如空关键词列表）
- **异步优先** — 全部 `async/await`

## 测试

- `tests/unit/test_analysis.py` — ContentSummarizer/TrendAnalyzer/SmartCrawlStrategy
- `tests/unit/test_wordcloud.py` — WordCloudGenerator 词云
- `tests/unit/test_cross_platform.py` — CrossPlatformAnalyzer 跨平台聚类
- `tests/unit/test_title_similarity.py` — Jaccard + 编辑距离相似度
