# Copyright (C) 2026 IoTchange - All Rights Reserved
# Author: 外星动物（常智） / IoTchange / 14455975@qq.com
"""SpideHarness Agent CLI — Typer 命令行接口.

用法:
    spide                    # 默认启动（交互模式）
    spide init               # 初始化工作空间
    spide config             # 配置向导
    spide doctor             # 环境检查
    spide crawl --source weibo   # 采集热搜
    spide run "分析今日热搜趋势"  # 运行 Agent 任务
    spide memory list        # 查看记忆
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import typer
from rich.console import Console
from rich.table import Table

from spide import __version__
from spide.workspace import (
    get_bootstrap_path,
    get_identity_path,
    get_memory_dir,
    get_memory_index_path,
    get_soul_path,
    get_user_path,
    get_workspace_root,
    initialize_workspace,
    workspace_health,
)

console = Console()
app = typer.Typer(
    name="spide",
    help="SpideHarness Agent — 热点新闻抓取 Agent CLI",
    no_args_is_help=False,
    invoke_without_command=True,
    add_completion=False,
)

# 子命令组
memory_app = typer.Typer(help="记忆管理")
timed_search_app = typer.Typer(help="定时搜索")
app.add_typer(memory_app, name="memory")
app.add_typer(timed_search_app, name="timed-search")


# ---------------------------------------------------------------------------
# 公共 Engine 会话上下文管理器
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _engine_session(
    workspace: str | None = None,
) -> AsyncGenerator[tuple, None]:
    """创建 Engine 会话，自动管理生命周期.

    用法:
        async with _engine_session(workspace) as (engine, bundle, settings):
            ...
    """
    from spide.config import load_settings
    from spide.harness import Engine

    settings = load_settings()
    engine = Engine(settings)
    try:
        bundle = await engine.start(workspace=workspace)
        yield engine, bundle, settings
    finally:
        await engine.stop()


# ---------------------------------------------------------------------------
# 回调：默认行为
# ---------------------------------------------------------------------------


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="显示版本号"),
) -> None:
    """SpideHarness Agent — 热点新闻抓取 Agent CLI."""
    if version:
        console.print(f"spide-agent {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        _show_welcome()


# ---------------------------------------------------------------------------
# init 命令
# ---------------------------------------------------------------------------


@app.command()
def init(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """初始化 SpideHarness Agent 工作空间."""
    root = initialize_workspace(workspace)
    console.print(f"[green]工作空间已初始化:[/green] {root}")

    template_files = [
        ("灵魂", get_soul_path(root)),
        ("用户画像", get_user_path(root)),
        ("身份", get_identity_path(root)),
        ("引导", get_bootstrap_path(root)),
        ("记忆索引", get_memory_index_path(root)),
    ]

    table = Table(title="模板文件")
    table.add_column("类型", style="cyan")
    table.add_column("路径", style="green")
    table.add_column("状态", style="yellow")

    for label, path in template_files:
        status = "新建" if path.exists() else "已存在"
        table.add_row(label, str(path), status)

    console.print(table)
    console.print("\n[yellow]下一步:[/yellow]")
    console.print("  1. 编辑 [cyan]~/.spide_agent/user.md[/cyan] 设置你的偏好")
    console.print("  2. 运行 [cyan]spide doctor[/cyan] 检查环境")


# ---------------------------------------------------------------------------
# config 命令
# ---------------------------------------------------------------------------


@app.command()
def config(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """配置 SpideHarness Agent."""
    console.print("[cyan]SpideHarness Agent 配置[/cyan]\n")

    settings_ok = _check_configs()
    if settings_ok:
        console.print("[green]当前配置文件完整[/green]")
    else:
        console.print("[yellow]部分配置文件缺失，请补充[/yellow]")
        console.print("  配置文件位于 [cyan]configs/[/cyan] 目录：")
        console.print("    - configs/default.yaml  (默认配置)")
        console.print("    - configs/llm.yaml      (LLM API Key)")
        console.print("    - configs/mqtt.yaml     (MQTT 凭证)")
        console.print("    - configs/uapi.yaml     (UAPI API Key)")


# ---------------------------------------------------------------------------
# doctor 命令
# ---------------------------------------------------------------------------


@app.command()
def doctor(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """环境健康检查."""
    console.print("[cyan]SpideHarness Agent 环境检查[/cyan]\n")

    all_ok = True

    # 1. 工作空间
    health = workspace_health(workspace)
    _print_health_table("工作空间", health)
    if not all(health.values()):
        all_ok = False
        console.print("[yellow]  提示: 运行 spide init 初始化[/yellow]\n")

    # 2. 配置文件
    configs_ok = _check_configs()
    if not configs_ok:
        all_ok = False

    # 3. Python 版本
    import sys

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 12)
    console.print(f"  Python {'[green]' if py_ok else '[red]'}{py_version}[/]")
    if not py_ok:
        all_ok = False
        console.print("[red]  需要 Python 3.12+[/red]")

    # 总结
    console.print()
    if all_ok:
        console.print("[green bold]所有检查通过！[/green bold]")
    else:
        console.print("[yellow bold]部分检查未通过，请按提示修复[/yellow bold]")


# ---------------------------------------------------------------------------
# crawl 命令
# ---------------------------------------------------------------------------


@app.command()
def crawl(
    source: str | None = typer.Option(
        None, "--source", "-s", help="数据源 (weibo/baidu/douyin/zhihu/bilibili)"
    ),
    all_sources: bool = typer.Option(False, "--all", "-a", help="采集所有已配置的数据源"),
    save: bool = typer.Option(False, "--save", help="保存采集结果到数据库"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """采集热搜数据."""
    asyncio.run(_crawl_async(source, all_sources, save, workspace))


async def _crawl_async(
    source: str | None,
    all_sources: bool,
    save_to_db: bool,
    workspace: str | None,
) -> None:
    """采集异步实现."""
    try:
        async with _engine_session(workspace) as (engine, bundle, settings):
            console.print(f"[cyan]会话 {bundle.session_id} 已启动[/cyan]\n")

            if source:
                console.print(f"[yellow]正在采集 {source} 热搜...[/yellow]")
                results = await engine.crawl(sources=[source])
                _display_crawl_results(results)
            elif all_sources:
                console.print("[yellow]正在采集所有热搜源...[/yellow]")
                results = await engine.crawl()
                _display_crawl_results(results)
            else:
                console.print("[red]请指定 --source <平台> 或 --all[/red]")
                raise typer.Exit(1) from None

            if save_to_db:
                from spide.storage.models import HotTopic
                from spide.storage.sqlite_repo import SqliteRepository

                db_path = settings.storage.sqlite_path
                repo = SqliteRepository(HotTopic, db_path=db_path)
                await repo.start()

                total = 0
                for _platform, topics in results.items():
                    ids = await repo.save_many(topics, dedup_fields=["title", "source"])
                    total += len(ids)

                await repo.stop()
                console.print(f"\n[green]已保存 {total} 条记录到 {db_path}[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]采集失败: {e}[/red]")
        raise typer.Exit(1) from None


def _display_crawl_results(results: dict[str, list]) -> None:
    """Rich 表格展示采集结果."""

    for platform, topics in results.items():
        if not topics:
            console.print(f"[yellow]{platform}: 无数据[/yellow]\n")
            continue

        table = Table(title=f"{platform} 热搜 ({len(topics)} 条)")
        table.add_column("排名", style="cyan", width=6)
        table.add_column("标题", style="white")
        table.add_column("热度", style="yellow", width=12)

        for topic in topics[:20]:
            hot_str = str(topic.hot_value) if topic.hot_value else "-"
            table.add_row(str(topic.rank or "-"), topic.title, hot_str)

        console.print(table)
        console.print()


# ---------------------------------------------------------------------------
# deep-crawl 命令
# ---------------------------------------------------------------------------


@app.command("deep-crawl")
def deep_crawl(
    platform: str = typer.Option(
        ..., "--platform", "-p", help="目标平台 (xhs/dy/ks/bili/wb/tieba/zhihu)"
    ),
    mode: str = typer.Option("search", "--mode", "-m", help="采集模式 (search/detail/creator)"),
    keywords: str | None = typer.Option(None, "--keywords", "-k", help="搜索关键词（逗号分隔）"),
    urls: str | None = typer.Option(None, "--urls", "-u", help="内容 URL 或 ID（逗号分隔）"),
    creators: str | None = typer.Option(None, "--creators", "-c", help="创作者 ID（逗号分隔）"),
    max_notes: int = typer.Option(20, "--max", help="最大采集数量"),
    comments: bool = typer.Option(True, "--comments/--no-comments", help="是否采集评论"),
    save: bool = typer.Option(False, "--save", help="保存到数据库"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="无头浏览器模式"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """深度采集（通过 MediaCrawler）— 需要浏览器环境."""
    asyncio.run(
        _deep_crawl_async(
            platform=platform,
            mode=mode,
            keywords=keywords,
            urls=urls,
            creators=creators,
            max_notes=max_notes,
            comments=comments,
            save=save,
            headless=headless,
            workspace=workspace,
        )
    )


async def _deep_crawl_async(
    *,
    platform: str,
    mode: str,
    keywords: str | None,
    urls: str | None,
    creators: str | None,
    max_notes: int,
    comments: bool,
    save: bool,
    headless: bool,
    workspace: str | None,
) -> None:
    """深度采集异步实现."""
    try:
        async with _engine_session(workspace) as (engine, bundle, settings):
            console.print(f"[cyan]会话 {bundle.session_id}[/cyan]")
            console.print(f"[dim]深度采集: {platform} / {mode}[/dim]\n")

            kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else None
            url_list = [u.strip() for u in urls.split(",") if u.strip()] if urls else None
            creator_list = [c.strip() for c in creators.split(",") if c.strip()] if creators else None

            results = await engine.deep_crawl(
                platform=platform,
                mode=mode,
                keywords=kw_list,
                content_ids=url_list,
                creator_ids=creator_list,
                max_notes=max_notes,
                enable_comments=comments,
                headless=headless,
            )

            contents = results.get("contents", [])
            comments_list = results.get("comments", [])
            creators_list = results.get("creators", [])

            console.print(f"[green]内容: {len(contents)} 条[/green]")
            console.print(f"[green]评论: {len(comments_list)} 条[/green]")
            console.print(f"[green]创作者: {len(creators_list)} 条[/green]")

            if contents:
                table = Table(title=f"{platform} 采集结果 ({len(contents)} 条)")
                table.add_column("标题", style="white", max_width=50)
                table.add_column("作者", style="cyan", width=12)
                table.add_column("点赞", style="yellow", width=8)
                table.add_column("评论", style="green", width=8)
                for item in contents[:20]:
                    table.add_row(
                        item.title[:50] if item.title else "-",
                        item.author_name[:12] if item.author_name else "-",
                        str(item.like_count or "-"),
                        str(item.comment_count or "-"),
                    )
                console.print(table)

            if save and contents:
                from spide.storage.models import DeepComment, DeepContent, DeepCreator
                from spide.storage.sqlite_repo import SqliteRepository

                db_path = settings.storage.sqlite_path

                repo = SqliteRepository(DeepContent, db_path=db_path)
                await repo.start()
                ids = await repo.save_many(contents)
                await repo.stop()
                console.print(f"\n[green]已保存 {len(ids)} 条内容到 {db_path}[/green]")

                if comments_list:
                    repo = SqliteRepository(DeepComment, db_path=db_path)
                    await repo.start()
                    ids = await repo.save_many(comments_list)
                    await repo.stop()
                    console.print(f"[green]已保存 {len(ids)} 条评论[/green]")

                if creators_list:
                    repo = SqliteRepository(DeepCreator, db_path=db_path)
                    await repo.start()
                    ids = await repo.save_many(creators_list)
                    await repo.stop()
                    console.print(f"[green]已保存 {len(ids)} 条创作者[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]深度采集失败: {e}[/red]")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# run 命令
# ---------------------------------------------------------------------------


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Agent 任务描述"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="流式输出"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """运行 Agent 任务."""
    asyncio.run(_run_async(prompt, stream, workspace))


async def _run_async(prompt: str, use_stream: bool, workspace: str | None) -> None:
    """Agent 运行异步实现."""
    try:
        async with _engine_session(workspace) as (engine, bundle, settings):
            console.print(f"[cyan]会话 {bundle.session_id}[/cyan]")
            console.print(f"[dim]模型: {bundle.settings.llm.text.model}[/dim]\n")

            if use_stream:
                stream = engine.chat_stream(prompt)
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        console.print(delta, end="")
                console.print("\n")
            else:
                response = engine.chat(prompt)
                content = response.choices[0].message.content  # type: ignore[attr-defined]
                console.print(content)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[red]运行失败: {e}[/red]")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# memory 子命令
# ---------------------------------------------------------------------------


@memory_app.command("list")
def memory_list(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """查看记忆文件列表."""
    root = get_workspace_root(workspace)
    mem_dir = get_memory_dir(root)

    if not mem_dir.is_dir():
        console.print("[yellow]记忆目录不存在，运行 spide init 初始化[/yellow]")
        return

    md_files = sorted(mem_dir.glob("*.md"))
    if not md_files:
        console.print("[yellow]暂无记忆文件[/yellow]")
        return

    for f in md_files:
        size = f.stat().st_size
        console.print(f"  {f.name}  [dim]({size} bytes)[/dim]")


@memory_app.command("add")
def memory_add(
    title: str = typer.Argument(..., help="记忆标题"),
    content: str = typer.Argument(..., help="记忆内容"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """添加记忆."""
    from spide.memory import add_memory

    path = add_memory(workspace, title=title, content=content)
    console.print(f"[green]记忆已添加:[/green] {path}")


# ---------------------------------------------------------------------------
# dashboard 命令
# ---------------------------------------------------------------------------


@app.command()
def dashboard(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出文件路径"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="自动打开浏览器"),
) -> None:
    """生成数据看板并在浏览器中打开."""
    asyncio.run(_dashboard_async(workspace, output, open_browser))


async def _dashboard_async(
    workspace: str | None, output: str | None, open_browser: bool
) -> None:
    """Dashboard 异步实现."""
    import webbrowser

    from spide.dashboard import collect_dashboard_data, render_dashboard
    from spide.dashboard.renderer import write_dashboard

    # 使用与 crawl 相同的数据库路径逻辑
    from spide.config import load_settings
    settings = load_settings()
    db_path = settings.storage.sqlite_path

    # 检查数据库是否存在
    if not Path(db_path).exists():
        console.print("[yellow]未找到数据库，请先运行:[/yellow] spide crawl")
        return

    data = await collect_dashboard_data(db_path=db_path)

    if data["total_count"] == 0:
        console.print("[yellow]数据库为空，请先运行:[/yellow] spide crawl")
        return

    html = render_dashboard(data)

    # 确定输出路径
    if output:
        out_path = Path(output)
    else:
        out_path = Path("dashboard") / "index.html"

    filepath = write_dashboard(html, out_path)
    # 转为绝对路径，确保 as_uri() 可用
    filepath = filepath.resolve()
    console.print(f"[green]看板已生成:[/green] {filepath}")
    console.print(f"[dim]数据: {data['total_count']} 条话题, {data['stats_summary']['platforms']} 个平台[/dim]")

    if open_browser:
        webbrowser.open(filepath.as_uri())
        console.print("[dim]已在浏览器中打开[/dim]")


# ---------------------------------------------------------------------------
# dedup 命令
# ---------------------------------------------------------------------------


@app.command()
def dedup(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不实际删除"),
) -> None:
    """清理数据库中的重复记录（按 title+source 去重）."""
    asyncio.run(_dedup_async(workspace, dry_run))


async def _dedup_async(workspace: str | None, dry_run: bool) -> None:
    """Dedup 异步实现."""
    from spide.config import load_settings
    from spide.storage.models import HotTopic
    from spide.storage.sqlite_repo import SqliteRepository

    settings = load_settings()
    db_path = settings.storage.sqlite_path

    if not Path(db_path).exists():
        console.print("[yellow]未找到数据库，请先运行:[/yellow] spide crawl")
        return

    repo = SqliteRepository(HotTopic, db_path=db_path)
    await repo.start()

    total = await repo.count()
    if total == 0:
        console.print("[yellow]数据库为空[/yellow]")
        await repo.stop()
        return

    # 查询所有记录
    all_topics = await repo.query(limit=total)

    # 按 (title, source) 分组，保留 hot_value 最高 + fetched_at 最新的一条
    groups: dict[tuple[str, str], list] = {}
    for t in all_topics:
        key = (t.title.strip().lower(), t.source.value)
        groups.setdefault(key, []).append(t)

    # 找出需要删除的 ID
    ids_to_delete: list[int] = []
    for key, items in groups.items():
        if len(items) <= 1:
            continue
        # 排序：hot_value 降序 → fetched_at 降序，保留第一条
        items.sort(key=lambda t: (t.hot_value or 0, t.fetched_at.isoformat() if t.fetched_at else ""), reverse=True)
        for item in items[1:]:
            if item.id is not None:
                ids_to_delete.append(item.id)

    await repo.stop()

    if not ids_to_delete:
        console.print(f"[green]数据库无重复记录 ({total} 条)[/green]")
        return

    # 输出预览
    distinct = len(groups)
    console.print(f"\n[bold]数据去重分析[/bold]")
    console.print(f"  总记录数:   {total}")
    console.print(f"  不重复:     {distinct}")
    console.print(f"  重复待清理: [red]{len(ids_to_delete)}[/red] 条")

    if dry_run:
        console.print("\n[yellow]--dry-run 模式，未实际删除。[/yellow]")
        return

    # 执行删除
    repo = SqliteRepository(HotTopic, db_path=db_path)
    await repo.start()
    deleted = 0
    for id_ in ids_to_delete:
        if await repo.delete(id_):
            deleted += 1
    await repo.stop()

    console.print(f"\n[green]已清理 {deleted} 条重复记录，保留 {total - deleted} 条[/green]")


# ---------------------------------------------------------------------------
# mcp-serve 命令
# ---------------------------------------------------------------------------


@app.command("mcp-serve")
def mcp_serve() -> None:
    """启动 MCP Server（stdio 模式，供外部 MCP 客户端连接）."""
    asyncio.run(_mcp_serve_async())


async def _mcp_serve_async() -> None:
    """MCP Server 异步启动."""
    from spide.mcp.server import serve_mcp

    await serve_mcp()


# ---------------------------------------------------------------------------
# mqtt 命令组
# ---------------------------------------------------------------------------


mqtt_app = typer.Typer(help="MQTT 通讯")
app.add_typer(mqtt_app, name="mqtt")


@mqtt_app.command("pub")
def mqtt_pub(
    topic: str = typer.Argument(..., help="发布主题"),
    payload: str = typer.Argument(..., help="消息内容"),
    qos: int = typer.Option(1, "--qos", help="QoS 级别"),
) -> None:
    """发布 MQTT 消息."""
    asyncio.run(_mqtt_pub_async(topic, payload, qos))


async def _mqtt_pub_async(topic: str, payload: str, qos: int) -> None:
    """MQTT 发布异步实现."""
    from spide.config import load_settings
    from spide.mqtt import MQTTClient

    settings = load_settings()
    client = MQTTClient(settings.mqtt)
    try:
        await client.start()
        await client.publish(topic, payload=payload, qos=qos)
        console.print(f"[green]已发布到 {topic}[/green]")
    except Exception as e:
        console.print(f"[red]发布失败: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        await client.stop()


@mqtt_app.command("sub")
def mqtt_sub(
    topic: str = typer.Argument(..., help="订阅主题"),
    count: int = typer.Option(10, "--count", "-n", help="接收消息数量后退出"),
) -> None:
    """订阅 MQTT 消息."""
    asyncio.run(_mqtt_sub_async(topic, count))


async def _mqtt_sub_async(topic: str, count: int) -> None:
    """MQTT 订阅异步实现."""
    from spide.config import load_settings
    from spide.mqtt import MQTTClient

    settings = load_settings()
    client = MQTTClient(settings.mqtt)
    try:
        await client.start()
        console.print(f"[cyan]已订阅 {topic}，等待 {count} 条消息...[/cyan]\n")

        received = 0
        async for message in client.subscribe(topic):
            payload = message.payload
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")  # type: ignore[assignment]
            console.print(f"  [yellow]{message.topic}[/yellow] → {payload}")  # type: ignore[str-bytes-safe]
            received += 1
            if received >= count:
                break
    except Exception as e:
        console.print(f"[red]订阅失败: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        await client.stop()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _show_welcome() -> None:
    """显示欢迎信息."""
    console.print(f"\n[bold cyan]SpideHarness Agent v{__version__}[/bold cyan]\n热点新闻抓取 Agent CLI\n")
    console.print("常用命令:")
    console.print("  [cyan]spide init[/cyan]          初始化工作空间")
    console.print("  [cyan]spide doctor[/cyan]        环境检查")
    console.print("  [cyan]spide crawl -s weibo[/cyan]     采集微博热搜")
    console.print('  [cyan]spide run "任务"[/cyan]       运行 Agent 任务')
    console.print("  [cyan]spide mcp-serve[/cyan]     启动 MCP Server")
    console.print("  [cyan]spide mqtt pub[/cyan]      发布 MQTT 消息")
    console.print("  [cyan]spide export -s weibo[/cyan]  导出数据")
    console.print("  [cyan]spide wordcloud -s weibo[/cyan]  生成词云")
    console.print("  [cyan]spide batch-crawl -p xhs,dy[/cyan]  批量采集")
    console.print("  [cyan]spide schedule start[/cyan]  定时调度")
    console.print("  [cyan]spide --help[/cyan]        查看所有命令\n")


# ---------------------------------------------------------------------------
# analyze 命令
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    source: str | None = typer.Option(
        None, "--source", "-s", help="数据源 (weibo/baidu/douyin/zhihu/bilibili)"
    ),
    keywords: str | None = typer.Option(None, "--keywords", "-k", help="分析关键词（逗号分隔）"),
    sentiment: bool = typer.Option(False, "--sentiment", help="对评论做情感分析"),
    strategy: bool = typer.Option(False, "--strategy", help="生成智能采集策略"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """AI 分析 — 智能摘要/情感分析/采集策略."""
    asyncio.run(_analyze_async(source, keywords, sentiment, strategy, workspace))


async def _analyze_async(
    source: str | None,
    keywords: str | None,
    do_sentiment: bool,
    do_strategy: bool,
    workspace: str | None,
) -> None:
    """AI 分析异步实现."""
    try:
        async with _engine_session(workspace) as (engine, bundle, settings):
            console.print(f"[cyan]会话 {bundle.session_id}[/cyan]\n")

        from spide.analysis.summarizer import ContentSummarizer, SmartCrawlStrategy, TrendAnalyzer

        summarizer = ContentSummarizer(bundle.llm)
        analyzer = TrendAnalyzer(bundle.llm)

        # 采集热搜作为分析输入
        if source and bundle.uapi:
            console.print(f"[yellow]正在采集 {source} 热搜...[/yellow]")
            topics = await bundle.uapi.fetch_hotboard(source)
            console.print(f"[green]获取 {len(topics)} 条热搜[/green]\n")

            # 趋势分析
            topics_data = [
                {"title": t.title, "hot_value": t.hot_value, "source": t.source.value}
                for t in topics
            ]
            trend = await analyzer.analyze(topics_data)
            console.print("[bold]热点趋势分析[/bold]")
            if "analysis" in trend:
                console.print(f"  {trend['analysis']}")
            if "top_categories" in trend:
                console.print(f"  热门分类: {', '.join(trend['top_categories'])}")
            if "hot_domains" in trend:
                console.print(f"  活跃领域: {', '.join(trend['hot_domains'])}")
            console.print()

            # 内容摘要（取 Top 3 热搜标题）
            if keywords or len(topics) > 0:
                console.print("[bold]热点内容摘要[/bold]")
                target_topics = topics[:3]
                for t in target_topics:
                    result = await summarizer.summarize(
                        title=t.title,
                        content=t.title,  # 热搜仅有标题，用标题作为内容
                        source=t.source.value,
                    )
                    if "error" not in result:
                        console.print(f"  [cyan]{t.title}[/cyan]")
                        console.print(f"  摘要: {result.get('summary', 'N/A')}")
                        console.print(f"  关键词: {', '.join(result.get('keywords', []))}")
                        console.print()

            # 智能采集策略
            if do_strategy:
                strategist = SmartCrawlStrategy(bundle.llm)
                result = await strategist.recommend(topics_data)
                console.print("[bold]智能采集策略[/bold]")
                if "analysis" in result:
                    console.print(f"  趋势分析: {result['analysis']}")
                if "search_keywords" in result:
                    console.print(f"  推荐关键词: {', '.join(result['search_keywords'])}")
                if "recommended_sources" in result:
                    console.print(f"  推荐来源: {', '.join(result['recommended_sources'])}")
                console.print()
        else:
            # 无数据源，用关键词直接分析
            if keywords:
                kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
                console.print(f"[yellow]分析关键词: {', '.join(kw_list)}[/yellow]\n")
                for kw in kw_list:
                    result = await summarizer.summarize(title=kw, content=kw)
                    if "error" not in result:
                        console.print(f"  [cyan]{kw}[/cyan]")
                        console.print(f"  分类: {result.get('category', 'N/A')}")
                        console.print(f"  关键词: {', '.join(result.get('keywords', []))}")
                        console.print()
            else:
                console.print("[red]请指定 --source 或 --keywords[/red]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]分析失败: {e}[/red]")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# export 命令
# ---------------------------------------------------------------------------


@app.command()
def export(
    source: str | None = typer.Option(
        None, "--source", "-s", help="数据源 (weibo/baidu/douyin/zhihu/bilibili)"
    ),
    fmt: str = typer.Option("json", "--format", "-f", help="导出格式 (json/jsonl/csv/excel)"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出目录"),
    filename: str | None = typer.Option(None, "--filename", "-n", help="文件名（不含扩展名）"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """导出热搜数据到文件（JSON/JSONL/CSV/Excel）."""
    asyncio.run(_export_async(source, fmt, output, filename, workspace))


async def _export_async(
    source: str | None,
    fmt: str,
    output_dir: str | None,
    filename: str | None,
    workspace: str | None,
) -> None:
    """数据导出异步实现."""
    try:
        async with _engine_session(workspace) as (engine, bundle, settings):
            console.print(f"[cyan]会话 {bundle.session_id}[/cyan]\n")

            if not source:
                console.print("[red]请指定 --source <平台>[/red]")
                raise typer.Exit(1) from None

            console.print(f"[yellow]正在采集 {source} 热搜...[/yellow]")
            results = await engine.crawl(sources=[source])
            topics = results.get(source, [])

            if not topics:
                console.print("[yellow]无数据可导出[/yellow]")
                return

            from spide.storage.exporter import DataExporter

            out_dir = output_dir or "data/export"
            fname = filename or f"{source}_hot"
            exporter = DataExporter(output_dir=out_dir)
            filepath = await exporter.export(topics, filename=fname, fmt=fmt)  # type: ignore[arg-type]

            console.print(f"[green]已导出 {len(topics)} 条数据到 {filepath}[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# wordcloud 命令
# ---------------------------------------------------------------------------


@app.command("wordcloud")
def wordcloud(
    source: str | None = typer.Option(
        None, "--source", "-s", help="数据源 (weibo/baidu/douyin/zhihu/bilibili)"
    ),
    texts: str | None = typer.Option(None, "--texts", "-t", help="直接提供文本（逗号分隔）"),
    output: str | None = typer.Option(None, "--output", "-o", help="输出目录"),
    filename: str | None = typer.Option("wordcloud", "--filename", "-n", help="文件名"),
    max_words: int = typer.Option(200, "--max-words", help="最大词数"),
    title: str | None = typer.Option(None, "--title", help="词云标题"),
    top_keywords: bool = typer.Option(False, "--top-keywords", help="仅输出高频关键词"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """生成词云图 — 从热搜标题或自定义文本."""
    asyncio.run(
        _wordcloud_async(source, texts, output, filename, max_words, title, top_keywords, workspace)
    )


async def _wordcloud_async(
    source: str | None,
    texts_str: str | None,
    output_dir: str | None,
    filename: str,
    max_words: int,
    title: str | None,
    show_keywords: bool,
    workspace: str | None,
) -> None:
    """词云生成异步实现."""
    from spide.analysis.wordcloud_generator import WordCloudGenerator

    out_dir = output_dir or "data/wordcloud"
    gen = WordCloudGenerator(output_dir=out_dir, max_words=max_words)

    try:
        if texts_str:
            text_list = [t.strip() for t in texts_str.split(",") if t.strip()]
            if show_keywords:
                freq = await gen.get_top_keywords(text_list, text_field="")
                console.print("[bold]高频关键词[/bold]")
                for word, count in freq:
                    console.print(f"  {word}: {count}")
                return

            filepath = await gen.generate_from_texts(text_list, filename=filename, title=title)
            console.print(f"[green]词云已生成: {filepath}[/green]")

        elif source:
            async with _engine_session(workspace) as (engine, bundle, settings):
                console.print(f"[cyan]会话 {bundle.session_id}[/cyan]")
                console.print(f"[yellow]正在采集 {source} 热搜标题...[/yellow]")

                results = await engine.crawl(sources=[source])
                topics = results.get(source, [])

                if not topics:
                    console.print("[yellow]无数据可生成词云[/yellow]")
                    return

                titles = [t.title for t in topics if t.title]

                if show_keywords:
                    freq = await gen.get_top_keywords(titles, text_field="")
                    console.print("[bold]高频关键词[/bold]")
                    for word, count in freq:
                        console.print(f"  {word}: {count}")
                    return

                filepath = await gen.generate_from_texts(
                    titles,
                    filename=f"{source}_wordcloud",
                    title=title or f"{source} 热搜词云",
                )
                console.print(f"[green]词云已生成: {filepath}[/green]")
        else:
            console.print("[red]请指定 --source <平台> 或 --texts <文本>[/red]")
            raise typer.Exit(1) from None

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]词云生成失败: {e}[/red]")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# batch-crawl 命令
# ---------------------------------------------------------------------------


@app.command("batch-crawl")
def batch_crawl(
    platforms: str = typer.Option(
        ..., "--platforms", "-p", help="平台列表（逗号分隔）: xhs,dy,ks,bili,wb,tieba,zhihu"
    ),
    keywords: str | None = typer.Option(None, "--keywords", "-k", help="搜索关键词（逗号分隔，所有平台共用）"),
    mode: str = typer.Option("search", "--mode", "-m", help="采集模式 (search/detail/creator)"),
    max_notes: int = typer.Option(10, "--max", help="每平台最大采集数"),
    concurrent: int = typer.Option(3, "--concurrent", "-c", help="最大并发数"),
    save: bool = typer.Option(False, "--save", help="保存到数据库"),
    export_fmt: str | None = typer.Option(None, "--export", "-e", help="导出格式 (json/csv/excel)"),
    output: str | None = typer.Option("data/export", "--output", "-o", help="导出目录"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """批量多平台深度采集 — 并行执行."""
    asyncio.run(
        _batch_crawl_async(platforms, keywords, mode, max_notes, concurrent, save, export_fmt, output, workspace)
    )


async def _batch_crawl_async(
    platforms_str: str,
    keywords_str: str | None,
    mode: str,
    max_notes: int,
    max_concurrent: int,
    save_to_db: bool,
    export_fmt: str | None,
    output_dir: str | None,
    workspace: str | None,
) -> None:
    """批量采集异步实现."""
    from spide.spider.batch_scheduler import BatchCrawlScheduler, BatchTask

    platform_list = [p.strip() for p in platforms_str.split(",") if p.strip()]
    kw_list = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str else []

    tasks = [
        BatchTask(platform=p, mode=mode, keywords=kw_list, max_notes=max_notes)
        for p in platform_list
    ]

    scheduler = BatchCrawlScheduler(max_concurrent=max_concurrent)
    console.print(f"[cyan]批量采集启动: {len(tasks)} 个平台，并发 {max_concurrent}[/cyan]\n")

    # 进度回调
    async def on_progress(completed: int, total: int, platform: str, status: str) -> None:
        icon = {"running": "...", "done": "OK", "failed": "FAIL"}.get(status, "?")
        console.print(f"  [{icon}] {platform} ({completed}/{total})")

    try:
        result = await scheduler.run(tasks, on_progress=on_progress)

        console.print("\n[bold]采集完成[/bold]")
        console.print(f"  成功: {', '.join(result.succeeded) or '无'}")
        console.print(f"  失败: {', '.join(result.failed.keys()) or '无'}")
        console.print(f"  内容: {result.total_contents} 条")
        console.print(f"  评论: {result.total_comments} 条")
        console.print(f"  创作者: {result.total_creators} 条")

        # 保存到数据库
        if save_to_db and (result.contents or result.comments or result.creators):
            from spide.config import load_settings
            from spide.storage.models import DeepComment, DeepContent, DeepCreator
            from spide.storage.sqlite_repo import SqliteRepository

            settings = load_settings()
            db_path = settings.storage.sqlite_path
            total_saved = 0

            if result.contents:
                repo = SqliteRepository(DeepContent, db_path=db_path)
                await repo.start()
                ids = await repo.save_many(result.contents)
                await repo.stop()
                total_saved += len(ids)

            if result.comments:
                repo = SqliteRepository(DeepComment, db_path=db_path)
                await repo.start()
                ids = await repo.save_many(result.comments)
                await repo.stop()
                total_saved += len(ids)

            if result.creators:
                repo = SqliteRepository(DeepCreator, db_path=db_path)
                await repo.start()
                ids = await repo.save_many(result.creators)
                await repo.stop()
                total_saved += len(ids)

            console.print(f"\n[green]已保存 {total_saved} 条记录到 {db_path}[/green]")

        # 导出
        if export_fmt and result.contents:
            from spide.storage.exporter import DataExporter

            exporter = DataExporter(output_dir=output_dir or "data/export")
            filepath = await exporter.export(result.contents, filename="batch_crawl", fmt=export_fmt)  # type: ignore[arg-type]
            console.print(f"[green]已导出到 {filepath}[/green]")

    except Exception as e:
        console.print(f"[red]批量采集失败: {e}[/red]")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# schedule 命令
# ---------------------------------------------------------------------------


@app.command()
def schedule(
    action: str = typer.Argument(..., help="操作: start / status / stop"),
    config: str | None = typer.Option(None, "--config", "-c", help="调度配置文件 (YAML)"),
    duration: int = typer.Option(0, "--duration", "-d", help="运行时长（秒），0=手动停止"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """定时采集调度 — 启动/查看/停止定时任务."""
    asyncio.run(_schedule_async(action, config, duration, workspace))


async def _schedule_async(
    action: str,
    config_path: str | None,
    duration: int,
    workspace: str | None,
) -> None:
    """定时调度异步实现."""
    from spide.spider.task_scheduler import ScheduledJob, TaskScheduler

    if action == "start":
        scheduler = TaskScheduler()

        # 从配置加载任务，或使用默认任务
        if config_path:
            from pathlib import Path

            import yaml

            config_file = Path(config_path)
            if not config_file.exists():
                console.print(f"[red]配置文件不存在: {config_path}[/red]")
                raise typer.Exit(1) from None

            with open(config_file, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)

            for job_cfg in cfg.get("jobs", []):
                job = ScheduledJob(
                    name=job_cfg["name"],
                    platforms=job_cfg.get("platforms", []),
                    sources=job_cfg.get("sources", []),
                    interval_seconds=job_cfg.get("interval", 300),
                    save_to_db=job_cfg.get("save", False),
                )
                scheduler.add_job(job)
        else:
            # 默认: 每个热搜源 5 分钟采集一次
            default_sources = ["weibo", "baidu", "zhihu"]
            for source in default_sources:
                scheduler.add_job(
                    ScheduledJob(
                        name=f"hot_{source}",
                        sources=[source],
                        interval_seconds=300,
                    ),
                )
            console.print("[dim]使用默认调度: 微博/百度/知乎 每 5 分钟[/dim]\n")

        # 注册结果回调
        async def on_result(data: dict) -> None:
            for key, items in data.items():
                console.print(f"  [green]{key}[/green]: {len(items)} 条")

        scheduler.on_result(on_result)
        await scheduler.start()

        console.print(f"[cyan]调度器已启动，{len(scheduler.jobs)} 个任务[/cyan]")

        try:
            if duration > 0:
                console.print(f"[dim]将在 {duration}s 后自动停止[/dim]")
                await asyncio.sleep(duration)
            else:
                console.print("[dim]按 Ctrl+C 停止[/dim]")
                # 永久运行直到被中断
                while True:
                    await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await scheduler.stop()
            console.print("\n[yellow]调度器已停止[/yellow]")

    elif action == "status":
        console.print("[cyan]调度器状态[/cyan]")
        console.print("  提示: 调度器为进程内运行，使用 `spide schedule status` 需配合外部进程管理")

    elif action == "stop":
        console.print("[yellow]请通过 Ctrl+C 或进程信号停止运行中的调度器[/yellow]")

    else:
        console.print(f"[red]未知操作: {action}，可选: start / status / stop[/red]")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# timed-search 命令组
# ---------------------------------------------------------------------------


@timed_search_app.command("start")
def timed_search_start(
    times: str = typer.Option("09:00,18:00", "--times", "-t", help="执行时间（逗号分隔），如 09:00,18:00"),
    sources: str = typer.Option("weibo,baidu,zhihu", "--sources", "-s", help="热搜源（逗号分隔）"),
    top_n: int = typer.Option(5, "--top", "-n", help="每个平台取 Top N 热搜"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """启动定时搜索 — 每日定时采集热搜并搜索关联新闻."""
    asyncio.run(_timed_search_start_async(times, sources, top_n, workspace))


async def _timed_search_start_async(
    times_str: str,
    sources_str: str,
    top_n: int,
    workspace: str | None,
) -> None:
    from spide.spider.task_scheduler import ScheduledJob, TaskScheduler
    from spide.spider.timed_search import TimedSearchService

    cron_times = [t.strip() for t in times_str.split(",") if t.strip()]
    source_list = [s.strip() for s in sources_str.split(",") if s.strip()]

    ws_root = _resolve_workspace(workspace)
    db_path = str(ws_root / "spide_data.db")

    service = TimedSearchService(db_path=db_path)
    await service.start()

    console.print(f"[cyan]定时搜索服务[/cyan]")
    console.print(f"  执行时间: [green]{', '.join(cron_times)}[/green]")
    console.print(f"  热搜源: [green]{', '.join(source_list)}[/green]")
    console.print(f"  每平台取 Top {top_n}")
    console.print(f"  数据库: {db_path}\n")

    # 用 TaskScheduler 的 cron 模式驱动
    scheduler = TaskScheduler()
    job = ScheduledJob(
        name="timed_search",
        sources=source_list,
        cron_times=cron_times,
    )

    async def on_timed_search(data: dict) -> None:
        result = await service.run_once(
            schedule_time=_current_schedule_time(cron_times),
            sources=source_list,
            top_n=top_n,
        )
        console.print(
            f"\n[green]✓ 搜索完成[/green] 批次={result['batch_key']} "
            f"热搜={result['total_topics']} 关联={result['search_count']}"
        )

    scheduler.add_job(job)
    scheduler.on_result(on_timed_search)
    await scheduler.start()

    console.print(f"[dim]调度器已启动，等待 {', '.join(cron_times)} 执行... (Ctrl+C 停止)[/dim]")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await scheduler.stop()
        await service.stop()
        console.print("\n[yellow]定时搜索服务已停止[/yellow]")


@timed_search_app.command("query")
def timed_search_query(
    schedule_time: str | None = typer.Option(None, "--time", "-t", help="按调度时间筛选，如 09:00"),
    limit: int = typer.Option(20, "--limit", "-n", help="返回条数"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="工作空间路径"),
) -> None:
    """查询定时搜索记录."""
    asyncio.run(_timed_search_query_async(schedule_time, limit, workspace))


async def _timed_search_query_async(
    schedule_time: str | None,
    limit: int,
    workspace: str | None,
) -> None:
    from spide.spider.timed_search import TimedSearchService

    ws_root = _resolve_workspace(workspace)
    db_path = str(ws_root / "spide_data.db")

    if not (ws_root / "spide_data.db").exists():
        console.print("[yellow]数据库不存在，请先运行 timed-search start[/yellow]")
        raise typer.Exit(0) from None

    service = TimedSearchService(db_path=db_path)
    await service.start()
    try:
        # 显示批次列表
        batches = await service.query_batches(limit=5)
        if batches:
            table = Table(title="搜索批次")
            table.add_column("批次", style="cyan")
            table.add_column("时间", style="green")
            table.add_column("热搜数", justify="right")
            table.add_column("搜索数", justify="right")
            table.add_column("状态")
            for b in batches:
                table.add_row(
                    b.get("batch_key", ""),
                    b.get("schedule_time", ""),
                    str(b.get("total_topics", 0)),
                    str(b.get("search_count", 0)),
                    b.get("status", ""),
                )
            console.print(table)
        else:
            console.print("[dim]暂无搜索批次记录[/dim]")

        # 显示搜索记录
        filters = {}
        if schedule_time:
            filters["schedule_time"] = schedule_time

        records = await service.query_records(limit=limit, **filters)
        if records:
            console.print(f"\n最近 {len(records)} 条搜索记录:")
            for r in records:
                console.print(
                    f"  [{r.get('schedule_time', '')}] "
                    f"[cyan]{r.get('topic_title', '')[:30]}[/cyan] → "
                    f"{r.get('search_title', '')[:40]}"
                )
                if r.get("search_snippet"):
                    console.print(f"    [dim]{r['search_snippet'][:60]}[/dim]")
    finally:
        await service.stop()


def _resolve_workspace(workspace: str | None) -> Path:
    """解析工作空间路径."""
    if workspace:
        return Path(workspace)
    from spide.workspace import get_workspace_root
    return get_workspace_root()


def _current_schedule_time(cron_times: list[str]) -> str:
    """根据当前时间匹配最近的 cron 时间."""
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute
    best = cron_times[0]
    best_diff = abs(now_minutes - int(best.split(":")[0]) * 60 - int(best.split(":")[1]))
    for t in cron_times[1:]:
        h, m = int(t.split(":")[0]), int(t.split(":")[1])
        diff = abs(now_minutes - h * 60 - m)
        if diff < best_diff:
            best = t
            best_diff = diff
    return best


@app.command("crawl-diff")
def crawl_diff(
    source: str = typer.Option("weibo", "--source", "-s", help="数据源平台"),
    last: bool = typer.Option(False, "--last", help="查看最近一次 diff"),
    history: bool = typer.Option(False, "--history", help="查看历史 diff 统计"),
    workspace: str | None = typer.Option(None, "--workspace", "-w"),
) -> None:
    """采集并对比增量差异."""
    asyncio.run(_crawl_diff_async(source, last, history, workspace))


async def _crawl_diff_async(
    source: str, last: bool, history: bool, workspace: str | None
) -> None:
    async with _engine_session(workspace) as (engine, bundle, settings):
        if last or history:
            from spide.storage.sqlite_repo import SqliteRepository
            from spide.storage.models import CrawlSnapshot

            repo = SqliteRepository(CrawlSnapshot, db_path=settings.storage.sqlite_path)
            await repo.start()
            try:
                snapshots = await repo.query(source=source, limit=10 if history else 1)
                if not snapshots:
                    console.print(f"[yellow]无 {source} 的历史快照[/yellow]")
                    return
                table = Table(title=f"{'历史' if history else '最近'} Diff — {source}")
                table.add_column("快照 Key", style="cyan")
                table.add_column("总数", justify="right")
                table.add_column("新增", style="green", justify="right")
                table.add_column("上升", style="yellow", justify="right")
                table.add_column("下降", style="red", justify="right")
                table.add_column("掉榜", style="dim", justify="right")
                table.add_column("时间", style="dim")
                for s in snapshots:
                    table.add_row(
                        s.snapshot_key,
                        str(s.total_topics),
                        str(s.new_count),
                        str(s.rising_count),
                        str(s.falling_count),
                        str(s.dropped_count),
                        s.created_at.strftime("%H:%M:%S"),
                    )
                console.print(table)
            finally:
                await repo.stop()
            return

        results = await engine.crawl_diff(sources=[source])
        diff_data = results.get(source, {})
        report = diff_data.get("report", {})
        changes = diff_data.get("changes", [])

        if not changes:
            console.print(f"[yellow]{source} 无变化数据[/yellow]")
            return

        summary = report.get("summary", {})
        console.print(f"\n[bold cyan]{source} 增量差异报告[/bold cyan]")
        console.print(f"  新增: [green]{summary.get('new', 0)}[/green]  "
                      f"上升: [yellow]{summary.get('rising', 0)}[/yellow]  "
                      f"下降: [red]{summary.get('falling', 0)}[/red]  "
                      f"掉榜: [dim]{summary.get('dropped', 0)}[/dim]")

        table = Table(title="话题变化详情")
        table.add_column("标题", style="cyan", max_width=40)
        table.add_column("状态", justify="center")
        table.add_column("热度变化", justify="right")
        for c in changes[:20]:
            status_colors = {"new": "green", "rising": "yellow", "falling": "red", "stable": "dim", "dropped": "dim"}
            color = status_colors.get(c.status.value, "white")
            change_str = f"+{c.hot_value_change}" if (c.hot_value_change or 0) > 0 else str(c.hot_value_change or "-")
            table.add_row(c.title[:40], f"[{color}]{c.status.value}[/{color}]", change_str)
        console.print(table)


@app.command("monitor")
def monitor(
    once: bool = typer.Option(False, "--once", help="单次检测"),
    rules: str | None = typer.Option(None, "--rules", "-r", help="告警规则文件路径"),
    interval: int = typer.Option(300, "--interval", "-i", help="检测间隔（秒）"),
    workspace: str | None = typer.Option(None, "--workspace", "-w"),
) -> None:
    """关键词监控与告警."""
    asyncio.run(_monitor_async(once, rules, interval, workspace))


async def _monitor_async(
    once: bool, rules_path: str | None, interval: int, workspace: str | None
) -> None:
    from spide.monitor.alert_engine import AlertEngine
    from spide.monitor.notifier import NotifierDispatcher

    rules = AlertEngine.load_rules(rules_path)
    if not rules:
        console.print("[yellow]无告警规则，请配置 --rules 或 configs/alert_rules.yaml[/yellow]")
        return

    engine_alert = AlertEngine(rules=rules)
    console.print(f"[green]已加载 {len(rules)} 条告警规则[/green]")
    for r in rules:
        console.print(f"  • {r.name}: {', '.join(r.keywords[:5])}")

    dispatcher = NotifierDispatcher()

    async with _engine_session(workspace) as (engine, bundle, settings):
        async def _check_once() -> None:
            sources = list(set(s.value for r in rules for s in r.sources)) or ["weibo", "baidu", "zhihu"]
            results = await engine.crawl(sources=sources)

            all_topics = []
            for src_topics in results.values():
                all_topics.extend(src_topics)

            alerts = engine_alert.evaluate(all_topics)
            if alerts:
                console.print(f"\n[bold red]触发 {len(alerts)} 条告警[/bold red]")
                for a in alerts:
                    console.print(f"  [{a.rule_name}] {a.topic_title} ({a.topic_source.value}) — {a.alert_type}")
                for a in alerts:
                    await dispatcher.dispatch(a, settings.alert.notification.channels)

        if once:
            await _check_once()
            return

        console.print(f"[dim]持续监控中，间隔 {interval}s，Ctrl+C 退出[/dim]")
        try:
            while True:
                await _check_once()
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            console.print("[dim]监控已停止[/dim]")


@app.command("track")
def track(
    source: str = typer.Option("weibo", "--source", "-s", help="数据源平台"),
    top: int = typer.Option(10, "--top", "-n", help="追踪 Top N"),
    workspace: str | None = typer.Option(None, "--workspace", "-w"),
) -> None:
    """热搜话题深度追踪（搜索 + 摘要 + 情感分析）."""
    asyncio.run(_track_async(source, top, workspace))


async def _track_async(source: str, top: int, workspace: str | None) -> None:
    async with _engine_session(workspace) as (engine, bundle, settings):
        results = await engine.crawl(sources=[source])
        topics = results.get(source, [])

        if not topics:
            console.print(f"[yellow]{source} 无热搜数据[/yellow]")
            return

        console.print(f"[cyan]追踪 {source} Top {top} 热搜...[/cyan]")
        tracks = await engine.track_deep(topics, top_n=top)

        table = Table(title=f"深度追踪 — {source} Top {top}")
        table.add_column("标题", style="cyan", max_width=30)
        table.add_column("状态", justify="center")
        table.add_column("情感", justify="center")
        table.add_column("摘要", max_width=50)
        table.add_column("关键词")

        for t in tracks:
            status_color = "green" if t.analysis_status == "completed" else "red"
            sentiment_color = {"positive": "green", "negative": "red", "neutral": "yellow", "mixed": "blue"}.get(t.sentiment, "dim")
            table.add_row(
                t.topic_title[:30],
                f"[{status_color}]{t.analysis_status}[/{status_color}]",
                f"[{sentiment_color}]{t.sentiment or '-'}[/{sentiment_color}]",
                t.summary[:50] if t.summary else "-",
                ", ".join(t.keywords[:3]),
            )
        console.print(table)


@app.command("cross-analyze")
def cross_analyze(
    report: bool = typer.Option(False, "--report", help="生成分析报告文件"),
    save: bool = typer.Option(False, "--save", help="结果持久化到 SQLite"),
    workspace: str | None = typer.Option(None, "--workspace", "-w"),
) -> None:
    """跨平台关联分析 — 语义聚类识别跨平台热点."""
    asyncio.run(_cross_analyze_async(report, save, workspace))


async def _cross_analyze_async(
    report: bool, save: bool, workspace: str | None
) -> None:
    async with _engine_session(workspace) as (engine, bundle, settings):
        sources = ["weibo", "baidu", "douyin", "zhihu", "bilibili"]
        console.print(f"[cyan]采集全平台热搜...[/cyan]")
        results = await engine.crawl(sources=sources)

        available = {k: v for k, v in results.items() if v}
        if not available:
            console.print("[yellow]无平台返回数据[/yellow]")
            return

        console.print(f"[cyan]分析 {len(available)} 个平台数据...[/cyan]")
        clusters = await engine.cross_analyze(available)

        table = Table(title="跨平台关联分析")
        table.add_column("聚类", style="cyan")
        table.add_column("平台", style="yellow")
        table.add_column("话题数", justify="right")
        table.add_column("跨平台", justify="center")
        table.add_column("分析", max_width=40)

        for c in clusters:
            cross = "[green]是[/green]" if c.cross_platform else "[dim]否[/dim]"
            table.add_row(
                c.cluster_name,
                ", ".join(c.platform_sources),
                str(len(c.topic_titles)),
                cross,
                c.analysis[:40],
            )
        console.print(table)

        if save:
            from spide.storage.sqlite_repo import SqliteRepository
            from spide.storage.models import TopicCluster

            repo = SqliteRepository(TopicCluster, db_path=settings.storage.sqlite_path)
            await repo.start()
            try:
                for c in clusters:
                    await repo.save(c)
            finally:
                await repo.stop()
            console.print(f"[green]已保存 {len(clusters)} 条聚类到 SQLite[/green]")

        if report:
            import json
            from pathlib import Path
            from datetime import datetime

            output_dir = Path("data/reports")
            output_dir.mkdir(parents=True, exist_ok=True)
            report_path = output_dir / f"cross_analyze_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path.write_text(
                json.dumps([c.model_dump(mode="json") for c in clusters], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            console.print(f"[green]报告已保存: {report_path}[/green]")


def _check_configs() -> bool:
    """检查配置文件是否存在."""
    from spide.config import load_settings

    try:
        settings = load_settings()
        has_llm = bool(settings.llm.common.api_key)
        has_uapi = bool(settings.uapi.api_key)
        has_mqtt = bool(settings.mqtt.host)

        checks = {
            "configs/llm.yaml (API Key)": has_llm,
            "configs/uapi.yaml (API Key)": has_uapi,
            "configs/mqtt.yaml (Host)": has_mqtt,
        }
        _print_health_table("配置文件", checks)
        return all(checks.values())
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        return False


def _print_health_table(title: str, checks: dict[str, bool]) -> None:
    """打印健康检查表格."""
    console.print(f"[bold]{title}[/bold]")
    for name, ok in checks.items():
        icon = "[green]OK[/green]" if ok else "[red]MISS[/red]"
        console.print(f"  {icon}  {name}")
    console.print()
