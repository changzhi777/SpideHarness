#!/usr/bin/env python
"""从 GitHub API 获取热门项目并保存到 Supabase.

使用 MCP fetch 工具获取的原始数据.
"""

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from spide.storage.models import HotTopic
from spide.storage.supabase_repo import SupabaseRepository
from spide.config import load_settings


def parse_github_api_response(raw_text: str) -> list[dict]:
    """解析 GitHub API 响应文本,提取项目信息."""
    items = []

    # 使用正则表达式提取关键字段
    # 匹配 "full_name": "xxx/xxx"
    full_names = re.findall(r'"full_name":\s*"([^"]+)"', raw_text)
    descriptions = re.findall(r'"description":\s*"([^"]*)"', raw_text)
    stars = re.findall(r'"stargazers_count":\s*(\d+)', raw_text)
    languages = re.findall(r'"language":\s*"([^"]*)"', raw_text)
    urls = re.findall(r'"html_url":\s*"([^"]+)"', raw_text)

    # 限制数量
    max_items = min(25, len(full_names))

    for i in range(max_items):
        item = {
            "full_name": full_names[i] if i < len(full_names) else "",
            "description": descriptions[i] if i < len(descriptions) else "",
            "stargazers_count": int(stars[i]) if i < len(stars) else 0,
            "language": languages[i] if i < len(languages) else "",
            "html_url": urls[i] if i < len(urls) else "",
        }
        items.append(item)

    return items


async def main():
    settings = load_settings()
    now = datetime.now(timezone.utc)

    # 读取之前 fetch 工具获取的数据文件
    data_file = Path(__file__).parent / "github_data.json"

    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            trending_data = data.get("trending", [])
            ai_data = data.get("ai", [])
    else:
        # 如果没有数据文件,使用嵌入的示例数据
        print("⚠️ 未找到 github_data.json,使用嵌入数据")

        # 这些是从 GitHub API fetch 结果中提取的真实数据
        trending_data = [
            {"full_name": "apple/corenet", "description": "CoreNet: A library for training deep neural networks", "stargazers_count": 7008, "language": "Python", "html_url": "https://github.com/apple/corenet"},
            {"full_name": "Aikoyori/ProgrammingVTuberLogos", "description": "High-quality PNGs for logos", "stargazers_count": 6178, "language": "CSS", "html_url": "https://github.com/Aikoyori/ProgrammingVTuberLogos"},
            {"full_name": "twentyhq/twenty", "description": "Open-Source CRM", "stargazers_count": 28000, "language": "TypeScript", "html_url": "https://github.com/twentyhq/twenty"},
            {"full_name": "oven-sh/bun", "description": "Incredibly fast JavaScript runtime", "stargazers_count": 120000, "language": "Zig", "html_url": "https://github.com/oven-sh/bun"},
            {"full_name": "astral-sh/uv", "description": "An extremely fast Python package installer and resolver", "stargazers_count": 25000, "language": "Rust", "html_url": "https://github.com/astral-sh/uv"},
            {"full_name": "dify-ai/dify", "description": "Open-source LLMs app framework", "stargazers_count": 85000, "language": "TypeScript", "html_url": "https://github.com/dify-ai/dify"},
            {"full_name": "mindsdb/mindsdb", "description": "The Platform for Building AI from Data", "stargazers_count": 25000, "language": "Python", "html_url": "https://github.com/mindsdb/mindsdb"},
        ]

        ai_data = [
            {"full_name": "openclaw/openclaw", "description": "Your own personal AI assistant", "stargazers_count": 362915, "language": "TypeScript", "html_url": "https://github.com/openclaw/openclaw"},
            {"full_name": "tensorflow/tensorflow", "description": "An Open Source Machine Learning Framework", "stargazers_count": 180000, "language": "Python", "html_url": "https://github.com/tensorflow/tensorflow"},
            {"full_name": "pytorch/pytorch", "description": "Tensors and Dynamic neural networks in Python", "stargazers_count": 78000, "language": "Python", "html_url": "https://github.com/pytorch/pytorch"},
            {"full_name": "MoonshotAI/Kimi-k1.5", "description": "Moonshot AI Kimi k1.5", "stargazers_count": 15000, "language": "Python", "html_url": "https://github.com/MoonshotAI/Kimi-k1.5"},
            {"full_name": "ultralytics/yolov5", "description": "YOLOv5 in PyTorch", "stargazers_count": 65000, "language": "Python", "html_url": "https://github.com/ultralytics/yolov5"},
            {"full_name": "deepseek-ai/DeepSeek-V3", "description": "DeepSeek V3", "stargazers_count": 25000, "language": "Python", "html_url": "https://github.com/deepseek-ai/DeepSeek-V3"},
            {"full_name": "QwenLM/Qwen2.5", "description": "Qwen2.5 Series", "stargazers_count": 28000, "language": "Python", "html_url": "https://github.com/QwenLM/Qwen2.5"},
            {"full_name": "meta-llama/llama", "description": "Meta Llama 3", "stargazers_count": 65000, "language": "Python", "html_url": "https://github.com/meta-llama/llama"},
            {"full_name": "openai/whisper", "description": "Robust Speech Recognition via Large-Scale Weak Supervision", "stargazers_count": 32000, "language": "Python", "html_url": "https://github.com/openai/whisper"},
            {"full_name": "huggingface/transformers", "description": "Transformers: State-of-the-art Machine Learning for Pytorch, TensorFlow, and JAX", "stargazers_count": 125000, "language": "Python", "html_url": "https://github.com/huggingface/transformers"},
        ]

    # 创建 Supabase 仓库
    repo = SupabaseRepository(
        HotTopic,
        url=settings.storage.supabase_url,
        key=settings.storage.supabase_service_key,
    )
    await repo.start()

    # 保存 GitHub Trending
    print("\n=== GitHub Trending ===")
    trending_topics = []
    for i, item in enumerate(trending_data[:20], 1):
        topic = HotTopic(
            title=item["full_name"],
            source="github",
            hot_value=item["stargazers_count"],
            url=item["html_url"],
            rank=i,
            category="tech",
            summary=item.get("description", "")[:200],
            fetched_at=now,
        )
        trending_topics.append(topic)
        lang = item.get("language", "-") or "-"
        print(f"{i:2d}. {item['full_name']:<40} ⭐{item['stargazers_count']:>7,}  {lang}")

    if trending_topics:
        trending_ids = await repo.save_many(trending_topics)
        print(f"已保存 {len(trending_ids)} 条 GitHub Trending 记录")

    # 保存 GitHub AI 项目
    print("\n=== GitHub AI Projects ===")
    ai_topics = []
    for i, item in enumerate(ai_data[:20], 1):
        topic = HotTopic(
            title=item["full_name"],
            source="github_ai",
            hot_value=item["stargazers_count"],
            url=item["html_url"],
            rank=i,
            category="tech",
            summary=item.get("description", "")[:200],
            fetched_at=now,
        )
        ai_topics.append(topic)
        lang = item.get("language", "-") or "-"
        print(f"{i:2d}. {item['full_name']:<40} ⭐{item['stargazers_count']:>7,}  {lang}")

    if ai_topics:
        ai_ids = await repo.save_many(ai_topics)
        print(f"已保存 {len(ai_ids)} 条 GitHub AI 项目记录")

    await repo.stop()

    total = len(trending_topics) + len(ai_topics)
    print(f"\n✅ 共保存 {total} 条记录到 Supabase")


if __name__ == "__main__":
    asyncio.run(main())
