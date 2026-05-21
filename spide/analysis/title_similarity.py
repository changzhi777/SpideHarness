# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""标题相似度计算 — jieba 分词 + Jaccard + 编辑距离.

用法:
    from spide.analysis.title_similarity import is_similar

    similar = is_similar("OpenAI发布GPT-5", "GPT-5正式发布OpenAI")  # True
    similar = is_similar("天气热", "股市暴跌")                       # False
"""

from __future__ import annotations

import jieba


def is_similar(a: str, b: str, threshold: float = 0.6) -> bool:
    """判断两个标题是否相似（综合 Jaccard + 编辑距离）.

    Args:
        a: 标题 A
        b: 标题 B
        threshold: 相似度阈值 (0.0~1.0)

    Returns:
        是否相似
    """
    if not a or not b:
        return False
    if a == b:
        return True

    jaccard = jaccard_similarity(a, b)
    edit = edit_similarity(a, b)

    # 加权综合：Jaccard 权重 0.4，编辑距离 0.6
    combined = jaccard * 0.4 + edit * 0.6
    return combined >= threshold


def jaccard_similarity(a: str, b: str) -> float:
    """基于 jieba 分词的 Jaccard 相似度."""
    set_a = set(jieba.cut(a))
    set_b = set(jieba.cut(b))

    # 过滤空白和标点
    set_a = {w.strip() for w in set_a if w.strip() and len(w.strip()) > 0}
    set_b = {w.strip() for w in set_b if w.strip() and len(w.strip()) > 0}

    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def edit_similarity(a: str, b: str) -> float:
    """基于编辑距离的相似度 (0.0~1.0)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    dist = _levenshtein_distance(a, b)
    max_len = max(len(a), len(b))
    return 1.0 - dist / max_len


def _levenshtein_distance(a: str, b: str) -> int:
    """Levenshtein 编辑距离."""
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n

    # 优化为两行 DP
    prev = list(range(m + 1))
    curr = [0] * (m + 1)

    for i in range(1, n + 1):
        curr[0] = i
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # 删除
                curr[j - 1] + 1,   # 插入
                prev[j - 1] + cost,  # 替换
            )
        prev, curr = curr, prev

    return prev[m]
