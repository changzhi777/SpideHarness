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
from pathlib import Path

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
app.add_typer(memory_app, name="memory")


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
    from spide.config import load_settings
    from spide.harness import Engine

    settings = load_settings()
    engine = Engine(settings)

    try:
        bundle = await engine.start(workspace=workspace)
        console.print(f"[cyan]会话 {bundle.session_id} 已启动[/cyan]\n")

        if source:
            # 单源采集
            console.print(f"[yellow]正在采集 {source} 热搜...[/yellow]")
            results = await engine.crawl(sources=[source])
            _display_crawl_results(results)
        elif all_sources:
            # 全源采集
            console.print("[yellow]正在采集所有热搜源...[/yellow]")
            results = await engine.crawl()
            _display_crawl_results(results)
        else:
            console.print("[red]请指定 --source <平台> 或 --all[/red]")
            raise typer.Exit(1) from None

        # 可选保存到数据库
        if save_to_db:
            from spide.storage import create_repo
            from spide.storage.models import HotTopic

            repo = create_repo(HotTopic, storage_config=settings.storage)
            await repo.start()

            total = 0
            for _platform, topics in results.items():
                ids = await repo.save_many(topics)
                total += len(ids)

            await repo.stop()
            console.print(f"\n[green]已保存 {total} 条记录[/green]")

    except Exception as e:
        console.print(f"[red]采集失败: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        await engine.stop()


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
    from spide.config import load_settings
    from spide.harness import Engine

    settings = load_settings()
    engine = Engine(settings)

    try:
        bundle = await engine.start(workspace=workspace)
        console.print(f"[cyan]会话 {bundle.session_id}[/cyan]")
        console.print(f"[dim]深度采集: {platform} / {mode}[/dim]\n")

        # 解析参数
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

        # 展示结果
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

        # 保存到数据库
        if save and contents:
            from spide.storage import create_repo
            from spide.storage.models import DeepComment, DeepContent, DeepCreator

            repo = create_repo(DeepContent, storage_config=settings.storage)
            await repo.start()
            ids = await repo.save_many(contents)
            await repo.stop()
            console.print(f"\n[green]已保存 {len(ids)} 条内容[/green]")

            if comments_list:
                repo = create_repo(DeepComment, storage_config=settings.storage)
                await repo.start()
                ids = await repo.save_many(comments_list)
                await repo.stop()
                console.print(f"[green]已保存 {len(ids)} 条评论[/green]")

            if creators_list:
                repo = create_repo(DeepCreator, storage_config=settings.storage)
                await repo.start()
                ids = await repo.save_many(creators_list)
                await repo.stop()
                console.print(f"[green]已保存 {len(ids)} 条创作者[/green]")

    except Exception as e:
        console.print(f"[red]深度采集失败: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        await engine.stop()


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
    from spide.config import load_settings
    from spide.harness import Engine

    settings = load_settings()
    engine = Engine(settings)

    try:
        bundle = await engine.start(workspace=workspace)
        console.print(f"[cyan]会话 {bundle.session_id}[/cyan]")
        console.print(f"[dim]模型: {bundle.settings.llm.text.model}[/dim]\n")

        if use_stream:
            stream = engine.chat_stream(prompt)
            full_text = ""
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    console.print(delta, end="")
                    full_text += delta
            console.print("\n")
        else:
            response = engine.chat(prompt)
            content = response.choices[0].message.content  # type: ignore[attr-defined]
            console.print(content)

    except Exception as e:
        console.print(f"\n[red]运行失败: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        await engine.stop()


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
    from spide.storage import create_repo
    from spide.storage.models import HotTopic

    settings = load_settings()

    if settings.storage.supabase_url:
        if dry_run:
            console.print("[yellow]Supabase 模式下不支持 --dry-run 预览[/yellow]")
        else:
            console.print("[green]Supabase 模式 — 数据库级 UNIQUE 约束自动去重，无需手动执行[/green]")
        return

    db_path = settings.storage.sqlite_path
    if not Path(db_path).exists():
        console.print("[yellow]未找到数据库，请先运行:[/yellow] spide crawl")
        return

    repo = create_repo(HotTopic, storage_config=settings.storage)
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
    repo = create_repo(HotTopic, storage_config=settings.storage)
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
    from spide.config import load_settings
    from spide.harness import Engine

    settings = load_settings()
    engine = Engine(settings)

    try:
        bundle = await engine.start(workspace=workspace)
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

    except Exception as e:
        console.print(f"[red]分析失败: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        await engine.stop()


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
    from spide.config import load_settings
    from spide.harness import Engine

    settings = load_settings()
    engine = Engine(settings)

    try:
        bundle = await engine.start(workspace=workspace)
        console.print(f"[cyan]会话 {bundle.session_id}[/cyan]\n")

        if not source:
            console.print("[red]请指定 --source <平台>[/red]")
            raise typer.Exit(1) from None

        # 采集数据
        console.print(f"[yellow]正在采集 {source} 热搜...[/yellow]")
        results = await engine.crawl(sources=[source])
        topics = results.get(source, [])

        if not topics:
            console.print("[yellow]无数据可导出[/yellow]")
            return

        # 导出
        from spide.storage.exporter import DataExporter

        out_dir = output_dir or "data/export"
        fname = filename or f"{source}_hot"
        exporter = DataExporter(output_dir=out_dir)
        filepath = await exporter.export(topics, filename=fname, fmt=fmt)  # type: ignore[arg-type]

        console.print(f"[green]已导出 {len(topics)} 条数据到 {filepath}[/green]")

    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")
        raise typer.Exit(1) from None
    finally:
        await engine.stop()


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
            # 直接用文本生成
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
            # 从热搜标题生成
            from spide.config import load_settings
            from spide.harness import Engine

            settings = load_settings()
            engine = Engine(settings)

            try:
                bundle = await engine.start(workspace=workspace)
                console.print(f"[cyan]会话 {bundle.session_id}[/cyan]")
                console.print(f"[yellow]正在采集 {source} 热搜标题...[/yellow]")

                results = await engine.crawl(sources=[source])
                topics = results.get(source, [])

                if not topics:
                    console.print("[yellow]无数据可生成词云[/yellow]")
                    return

                # 用热搜标题作为文本
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

            finally:
                await engine.stop()
        else:
            console.print("[red]请指定 --source <平台> 或 --texts <文本>[/red]")
            raise typer.Exit(1) from None

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
            from spide.storage import create_repo
            from spide.storage.models import DeepComment, DeepContent, DeepCreator

            settings = load_settings()
            total_saved = 0

            if result.contents:
                repo = create_repo(DeepContent, storage_config=settings.storage)
                await repo.start()
                ids = await repo.save_many(result.contents)
                await repo.stop()
                total_saved += len(ids)

            if result.comments:
                repo = create_repo(DeepComment, storage_config=settings.storage)
                await repo.start()
                ids = await repo.save_many(result.comments)
                await repo.stop()
                total_saved += len(ids)

            if result.creators:
                repo = create_repo(DeepCreator, storage_config=settings.storage)
                await repo.start()
                ids = await repo.save_many(result.creators)
                await repo.stop()
                total_saved += len(ids)

            console.print(f"\n[green]已保存 {total_saved} 条记录[/green]")

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
