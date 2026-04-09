# install.ps1 — Spide Agent 一键安装脚本 (Windows)
#
# 用法:
#   .\install.ps1                       # 默认安装到当前目录
#   .\install.ps1 -InstallDir C:\spide # 指定安装目录
#   .\install.ps1 -SkipSkills          # 跳过 AI Skills 安装
#   .\install.ps1 -VerifyOnly          # 仅验证安装状态

[CmdletBinding()]
param(
    [string]$InstallDir = $PSScriptRoot,
    [switch]$SkipSkills = $false,
    [switch]$VerifyOnly = $false
)

# ── 输出函数 ──────────────────────────────────────────────────
function Write-Step([string]$Num, [string]$Msg) {
    Write-Host ""
    Write-Host "[STEP $Num] $Msg" -ForegroundColor Cyan
}

function Write-Info([string]$Msg)  { Write-Host "  * $Msg" -ForegroundColor Blue }
function Write-Ok([string]$Msg)    { Write-Host "  [OK] $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg)  { Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-Err([string]$Msg)   { Write-Host "  [ERROR] $Msg" -ForegroundColor Red }

# ── 版本提取 ──────────────────────────────────────────────────
$Version = "unknown"
$initFile = Join-Path $InstallDir "spide\__init__.py"
if (Test-Path $initFile) {
    $content = Get-Content $initFile -Raw
    if ($content -match '__version__\s*=\s*"([^"]+)"') {
        $Version = $Matches[1]
    }
}

# ── Banner ────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor White
Write-Host "  Spide Agent $Version 安装程序" -ForegroundColor White
Write-Host "============================================" -ForegroundColor White

# ── 验证模式 ──────────────────────────────────────────────────
if ($VerifyOnly) {
    Write-Host ""
    Write-Info "验证安装状态..."
    Write-Host ""

    $errors = 0

    # Python
    try {
        $pyVer = python --version 2>&1
        Write-Ok "Python: $pyVer"
    } catch {
        Write-Err "Python: 未安装"
        $errors++
    }

    # uv
    try {
        $uvVer = uv --version 2>&1
        Write-Ok "uv: $uvVer"
    } catch {
        Write-Err "uv: 未安装"
        $errors++
    }

    # 配置文件
    foreach ($cfg in @("configs\llm.yaml", "configs\uapi.yaml")) {
        if (Test-Path (Join-Path $InstallDir $cfg)) {
            Write-Ok "配置: $cfg"
        } else {
            Write-Warn "配置: $cfg 不存在（需要填写 API Key）"
        }
    }

    # Skills
    $skillsDir = Join-Path $InstallDir ".claude\skills"
    if (Test-Path $skillsDir) {
        $skillCount = (Get-ChildItem $skillsDir -Directory).Count
        Write-Ok "Skills: $skillCount 个已安装"
    } else {
        Write-Warn "Skills: 未安装"
    }

    Write-Host ""
    if ($errors -eq 0) {
        Write-Ok "验证通过"
    } else {
        Write-Err "发现 $errors 个问题"
        exit 1
    }
    exit 0
}

# ── Step 1: 环境检查 ──────────────────────────────────────────
Write-Step 1 "环境检查"

# Python 3.12+
$pyCmd = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $verOutput = & $cmd --version 2>&1
        if ($verOutput -match '(\d+)\.(\d+)') {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
                $pyCmd = $cmd
                Write-Ok "Python: $verOutput"
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $pyCmd) {
    Write-Err "需要 Python 3.12+"
    Write-Info "下载地址: https://www.python.org/downloads/"
    exit 1
}

# uv
try {
    $uvVer = uv --version 2>&1
    Write-Ok "uv: $uvVer"
} catch {
    Write-Err "uv 未安装"
    Write-Info "安装指南: https://docs.astral.sh/uv/getting-started/installation/"
    Write-Host ""
    Write-Info "快速安装 (PowerShell):"
    Write-Info "  irm https://astral.sh/uv/install.ps1 | iex"
    exit 1
}

# ── Step 2: 安装依赖 ──────────────────────────────────────────
Write-Step 2 "安装 Python 依赖 (uv sync)"

Set-Location $InstallDir

if (Test-Path ".venv") {
    Write-Warn "检测到已有 .venv/，将重新同步依赖"
}

& uv sync 2>&1 | ForEach-Object { Write-Host "  $_" }

if ($LASTEXITCODE -ne 0) {
    Write-Err "uv sync 失败"
    Write-Info "请检查网络连接和 pyproject.toml 依赖配置"
    exit 1
}

Write-Ok "依赖安装完成"

# ── Step 3: 生成配置模板 ──────────────────────────────────────
Write-Step 3 "生成配置模板"

$configsDir = Join-Path $InstallDir "configs"
if (-not (Test-Path $configsDir)) {
    New-Item -ItemType Directory -Path $configsDir -Force | Out-Null
}

# llm.yaml
$llmPath = Join-Path $configsDir "llm.yaml"
if (Test-Path $llmPath) {
    Write-Warn "configs\llm.yaml 已存在，跳过"
} else {
    @"
# Spide Agent LLM 配置
# 请填写智谱 AI API Key（https://open.bigmodel.cn）
common:
  provider: "zhipuai"
  api_key: "YOUR_ZHIPUAI_API_KEY"    # <-- 替换为你的 API Key
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  sdk: "zai"

text:
  model: "glm-5.1"
  max_tokens: 4096
  temperature: 0.7
  thinking_type: "enabled"
  stream: true

vision:
  model: "glm-5v-turbo"
  max_tokens: 4096
  temperature: 0.7

web_search:
  engine: "search_pro"
  default_count: 15
  content_size: "high"
  recency_filter: "noLimit"
"@ | Out-File -FilePath $llmPath -Encoding UTF8
    Write-Ok "已生成 configs\llm.yaml（请填写 API Key）"
}

# mqtt.yaml
$mqttPath = Join-Path $configsDir "mqtt.yaml"
if (Test-Path $mqttPath) {
    Write-Warn "configs\mqtt.yaml 已存在，跳过"
} else {
    @"
# Spide Agent MQTT 配置
# 如果不使用 MQTT 功能，可以保持默认值
host: "YOUR_MQTT_HOST"       # <-- 替换为 MQTT 服务器地址（可选）
port: 8883
username: ""
password: ""
use_tls: true
reconnect:
  max_retries: 5
  backoff_base: 1.0
  backoff_max: 30.0
"@ | Out-File -FilePath $mqttPath -Encoding UTF8
    Write-Ok "已生成 configs\mqtt.yaml（MQTT 为可选功能）"
}

# uapi.yaml
$uapiPath = Join-Path $configsDir "uapi.yaml"
if (Test-Path $uapiPath) {
    Write-Warn "configs\uapi.yaml 已存在，跳过"
} else {
    @"
# Spide Agent UAPI 数据源配置
# 请填写 UAPI API Key（https://uapis.cn）
api_key: "YOUR_UAPI_API_KEY"  # <-- 替换为你的 API Key

hot_sources:
  - name: "weibo"
    alias: "微博热搜"
    refresh_interval: 300
  - name: "baidu"
    alias: "百度热搜"
    refresh_interval: 300
  - name: "douyin"
    alias: "抖音热点"
    refresh_interval: 180
  - name: "zhihu"
    alias: "知乎热榜"
    refresh_interval: 300
  - name: "bilibili"
    alias: "B站热搜"
    refresh_interval: 300

rate_limit:
  max_concurrent: 5
  requests_per_minute: 30

retry:
  max_retries: 3
  backoff_base: 1.0
  backoff_max: 30.0
"@ | Out-File -FilePath $uapiPath -Encoding UTF8
    Write-Ok "已生成 configs\uapi.yaml（请填写 API Key）"
}

# ── Step 4: 初始化工作空间 ─────────────────────────────────────
Write-Step 4 "初始化 Spide 工作空间"

& uv run spide init 2>&1 | ForEach-Object { Write-Host "  $_" }

if ($LASTEXITCODE -eq 0) {
    Write-Ok "工作空间初始化完成"
} else {
    Write-Warn "工作空间初始化失败（可能需要手动运行: uv run spide init）"
}

# ── Step 5: 安装 AI Skills ─────────────────────────────────────
Write-Step 5 "安装 AI Agent Skills"

if ($SkipSkills) {
    Write-Warn "已跳过 Skills 安装（-SkipSkills）"
} else {
    $skillsScript = Join-Path $InstallDir "install-skills.sh"
    if (Test-Path $skillsScript) {
        # Windows 下用 bash 执行（需要 Git Bash）
        $bashPath = Get-Command bash -ErrorAction SilentlyContinue
        if ($bashPath) {
            & bash install-skills.sh --claude 2>&1 | ForEach-Object { Write-Host "  $_" }
            Write-Ok "Skills 安装完成"
        } else {
            # 无 bash 时手动复制
            Write-Info "未检测到 bash，使用手动复制方式安装 Skills..."
            $claudeSkillsDir = Join-Path $InstallDir ".claude\skills"
            if (-not (Test-Path $claudeSkillsDir)) {
                New-Item -ItemType Directory -Path $claudeSkillsDir -Force | Out-Null
            }
            $skillsDir = Join-Path $InstallDir "skills"
            if (Test-Path $skillsDir) {
                Get-ChildItem $skillsDir -Directory | ForEach-Object {
                    $dst = Join-Path $claudeSkillsDir $_.Name
                    if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
                    Copy-Item $_.FullName $dst -Recurse
                    Write-Ok "$($_.Name) -> .claude\skills\$($_.Name)"
                }
            }
            Write-Ok "Skills 安装完成"
        }
    } else {
        Write-Warn "install-skills.sh 不存在，跳过 Skills 安装"
    }
}

# ── Step 6: MediaCrawler 检查 ──────────────────────────────────
Write-Step 6 "检查深度采集组件"

$mcDir = Join-Path $InstallDir "MediaCrawler"
if (Test-Path $mcDir) {
    Write-Ok "MediaCrawler 已就绪（支持 7 平台深度采集）"
} else {
    Write-Warn "MediaCrawler 不存在（深度采集功能不可用）"
    Write-Info "深度采集为可选功能，基本的热搜采集不受影响"
    Write-Info "如需深度采集，请单独下载 MediaCrawler 到本项目根目录"
}

# ── Step 7: 环境健康检查 ───────────────────────────────────────
Write-Step 7 "环境健康检查"

& uv run spide doctor 2>&1 | ForEach-Object { Write-Host "  $_" }

Write-Ok "健康检查完成"

# ── Step 8: 安装摘要 ──────────────────────────────────────────
Write-Host ""
Write-Host "============================================" -ForegroundColor White
Write-Host "  安装完成!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor White
Write-Host ""
Write-Host "  安装目录: $InstallDir" -ForegroundColor White
Write-Host "  版本:     $Version" -ForegroundColor White
Write-Host ""
Write-Host "  下一步:" -ForegroundColor White
Write-Host ""
Write-Host "  1. 编辑配置文件，填写 API Key:" -ForegroundColor White
Write-Host "     configs\llm.yaml   - 智谱 AI API Key" -ForegroundColor Yellow
Write-Host "     configs\uapi.yaml  - UAPI 数据源 Key" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. 验证环境:" -ForegroundColor White
Write-Host "     uv run spide doctor" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. 开始使用:" -ForegroundColor White
Write-Host "     uv run spide crawl -s weibo       # 采集微博热搜" -ForegroundColor Yellow
Write-Host "     uv run spide crawl --all          # 采集所有热搜源" -ForegroundColor Yellow
Write-Host "     uv run spide analyze -s baidu     # 分析百度热搜" -ForegroundColor Yellow
Write-Host ""
Write-Host "  文档: README.md | docs\skills-guide.md" -ForegroundColor White
Write-Host ""
