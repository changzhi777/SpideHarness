# AI 分析模块

> [根目录](../../CLAUDE.md) → `spide/analysis/`

## 职责

基于 LLM 的智能分析能力，包括内容摘要、趋势分析、智能采集策略、词云生成和跨平台关联分析。

## 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 3 | 模块初始化 |
| `summarizer.py` | 309 | ContentSummarizer + TrendAnalyzer + SmartCrawlStrategy |
| `wordcloud_generator.py` | 218 | WordCloudGenerator — jieba 分词 + wordcloud 生成 |
| `cross_platform.py` | 193 | CrossPlatformAnalyzer — LLM 语义聚类 + 跨平台去重 |
| `title_similarity.py` | 95 | jieba Jaccard + Levenshtein 编辑距离相似度 |

## 核心类

### ContentSummarizer
```python
summarizer = ContentSummarizer(llm_client)
result = await summarizer.summarize(title="标题", content="正文")
keywords = await summarizer.extract_keywords(title="...", content="...")
sentiment = await summarizer.analyze_sentiment(comments=["好文", "垃圾"])
```

### TrendAnalyzer
```python
analyzer = TrendAnalyzer(llm_client)
result = await analyzer.analyze(current_topics, previous_topics)
```

### CrossPlatformAnalyzer
```python
analyzer = CrossPlatformAnalyzer(llm_client)
clusters = await analyzer.analyze({"weibo": topics1, "zhihu": topics2})
```

### title_similarity
```python
from spide.analysis.title_similarity import is_similar
similar = is_similar("标题A", "标题B", threshold=0.6)
```

## 依赖

- `spide.llm` (LLMClient) — summarizer/trend/strategy/cross_platform
- jieba — 中文分词
- wordcloud — 词云生成

## 测试

- `tests/unit/test_analysis.py`
- `tests/unit/test_wordcloud.py`
- `tests/unit/test_cross_platform.py`
- `tests/unit/test_title_similarity.py`
