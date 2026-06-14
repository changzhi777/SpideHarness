# Thoth 知识库集成

> V3.1.4+ 新增 — spide 与 Thoth 知识库的 HTTP 集成

## 架构

```
┌─────────────────┐  Bearer Token   ┌──────────────────────┐
│  spide 服务     │ ──────────────→ │  Thoth 10.10.10.15:8765 │
│  (本机)         │   HTTP          │  (FastAPI 1.0.32)   │
│  ThothClient    │ ←────────────── │  /api/notes         │
└─────────────────┘  JSON Response  └──────────────────────┘
                            │
                            └──→ PostgreSQL 10.10.10.11
                                Redis 10.10.10.18
```

## 配置

`configs/thoth.yaml`（参考 `feishu.yaml` 模式，使用 `${ENV_VAR}` 占位符）：

```yaml
thoth:
  base_url: "http://10.10.10.15:8765"
  token: "${THOTH_API_TOKEN:}"   # 环境变量 THOTH_API_TOKEN
  default_room_id: "room_video_2026"   # 按年分类
  timeout: 30.0
```

**Token 获取**（因 Thoth PG 限制，register 暂不可用）：

1. 浏览器打开 Thoth Web UI：`http://10.10.10.15:8765`
2. DevTools → Network → 任意请求 → 复制 `Authorization: Bearer xxx` 的值
3. 临时方案：直接填入 `configs/thoth.yaml` 的 `token:` 字段
4. 推荐方案：导出 `export THOTH_API_TOKEN=xxx`（不入 Git）

## Python API

```python
from spide.config import load_settings
from spide.integrations import ThothClient, ThothAuthError

settings = load_settings()
client = ThothClient(settings.thoth)
try:
    await client.start()
    # 1. 健康检查（公开端点，不需 token）
    if not await client.health_check():
        logger.error("Thoth 不可达")
        return

    # 2. 创建知识库笔记
    note = await client.create_note(
        title="GPT-5 综述",
        content="# GPT-5\n\n核心要点...",
        tags="AI,LLM",
        room_id="room_video_2026",   # 可选，默认从配置读
    )
    note_id = note["id"]

    # 3. 搜索
    results = await client.search_notes("GPT-5", room_id="room_video_2026")

    # 4. 更新
    await client.update_note(note_id, content="# GPT-5\n\n更新内容...")

    # 5. 删除
    await client.delete_note(note_id)
finally:
    await client.stop()
```

## 异常体系

```python
ThothError (基类, status_code)
├── ThothAuthError         # 401/403 — token 失效
├── ThothNotFoundError     # 404
└── ThothServerError       # 5xx — 服务端错误（可重试）
```

所有异常继承自 `SpideError`（项目统一异常基类）。

## 重试策略

| HTTP 状态 | 行为 |
|----------|------|
| 2xx | 成功 |
| 400, 422 | 立即抛 ThothError（参数错误，重试无意义）|
| 401, 403 | 立即抛 ThothAuthError（不重试，token 失效）|
| 404 | 立即抛 ThothNotFoundError |
| 5xx | 重试 3 次（指数退避 0.5/1/2s）→ 抛 ThothServerError |
| 网络错误 (ClientError) | 重试 3 次 → 抛 ThothError |

## 端点映射

| 方法 | Thoth 端点 | 用途 |
|------|-----------|------|
| `health_check()` | `GET /api/status` | 健康检查（公开）|
| `create_note(...)` | `POST /api/notes` | 创建笔记 |
| `get_note(id)` | `GET /api/notes/{id}` | 获取笔记 |
| `search_notes(q)` | `POST /api/notes/search` | 搜索 |
| `update_note(id, **fields)` | `PUT /api/notes/{id}` | 更新 |
| `delete_note(id)` | `DELETE /api/notes/{id}` | 删除 |

## 测试

`tests/unit/test_thoth_client.py`（25 用例）：

```bash
uv run pytest tests/unit/test_thoth_client.py -v
```

## 已知限制

- **Thoth PG sslmode**：Thoth PostgreSQL 当前因 `pg_hba.conf` 拒绝明文连接，register/login 暂不可用
- **Token 需手动获取**：从 Web UI DevTools 拿
- **`/api/notes/search` 返回结构容错**：list 直接返回，dict.items 提取，其他返回空

## 后续扩展

- 飞书消息 → 视频文章保存（V3.1.5+ 待实现）
- 视频分析结果自动转换为 Markdown 文章
- 定时任务：每日新增视频 → 增量同步到 Thoth
