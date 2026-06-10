# PVE 部署 + 公网回调配置手册

> SpideHarness Agent 在 PVE 容器 + 家庭网络中的完整部署流程。
> 涉及：CT107 容器（Dashboard）、PVE 宿主机（Nginx 反代）、家庭防火墙（端口映射）、飞书开发者后台（事件订阅）。

## 部署架构

```
┌────────────────────────────────────────────────────────────────────┐
│                        飞书服务器 (open.feishu.cn)                  │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ HTTPS (443)
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  家庭防火墙 / 路由器 (公网 IPv6 + IPv4)                              │
│  - 防火墙规则: 允许入站 IPv6 443 → 10.10.10.10:8443                │
│  - 防火墙规则: 允许入站 IPv4 443 → 10.10.10.10:8443 (可选)        │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ 内网 (vmbr0)
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  PVE 宿主机 (10.10.10.10)                                          │
│  - Nginx 1.26 (SSL termination)                                   │
│  - 监听: 8443 (HTTPS) / 8088 (HTTP)                                │
│  - 证书: /etc/nginx/ssl/spide.crt + spide.key (自签 ECC)          │
│  - 反代: 10.10.10.16:8765 (CT107 实际 IP)                          │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ 内网
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  CT107 LXC 容器 (10.10.10.16, 256MB RAM)                            │
│  - Dashboard (uvicorn) 监听 0.0.0.0:8765                            │
│  - SQLite /data/Spide_agent/spide_data.db                          │
│  - LLM: 转发到 10.10.10.138:8001 (家庭内 MLX Gemma 4 e4b)          │
└────────────────────────────────────────────────────────────────────┘
```

## 一、CT107 容器部署

### 1.1 准备环境

```bash
# PVE 宿主机执行
pct create 107 local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname QM-Spide \
  --cores 2 --memory 256 --swap 512 \
  --rootfs local-zfs:8 \
  --net0 name=eth0,bridge=vmbr0,ip=10.10.10.16/24,gw=10.10.10.5 \
  --features nesting=1 \
  --unprivileged 1 \
  --onboot 1 \
  --ostype debian
pct start 107
```

### 1.2 安装系统依赖

```bash
pct enter 107
apt update && apt install -y python3 python3-pip curl wget
```

### 1.3 安装 uv（管理 Python 3.12）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH=/root/.local/bin:$PATH
echo 'export PATH=/root/.local/bin:$PATH' >> ~/.bashrc
```

### 1.4 同步代码 + 安装依赖

```bash
# 在本地 macOS 工作站
cd /Users/mac/Documents/trae_projects/Spide_agent
tar -czf /tmp/Spide_agent.tar.gz \
  --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
  --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='*.db' \
  --exclude='output/' --exclude='data/' --exclude='sessions/' \
  --exclude='*.log' --exclude='.claude/' --exclude='.zcf/' \
  --exclude='.playwright-mcp/' --exclude='MediaCrawler/' --exclude='OpenHarness/' \
  --exclude='OpenCLI/' --exclude='CA/' \
  .

scp /tmp/Spide_agent.tar.gz root@10.10.10.10:/tmp/
ssh root@10.10.10.10 "pct push 107 /tmp/Spide_agent.tar.gz /tmp/Spide_agent.tar.gz"

ssh root@10.10.10.10 "pct exec 107 -- bash -c '
  mkdir -p /opt
  cd /opt
  tar -xzf /tmp/Spide_agent.tar.gz
  mv Spide_agent Spide_agent
  cd /opt/Spide_agent
  export PATH=/root/.local/bin:\$PATH
  uv sync
'"
```

### 1.5 配置环境变量（敏感信息）

```bash
# 在 CT107 上创建 /root/.spide/env.sh
mkdir -p /root/.spide
cat > /root/.spide/env.sh << 'EOF'
# SpideHarness Agent 环境变量（CT107 部署）
# 加载方式: source /root/.spide/env.sh

# 飞书智能体
export SPIDE_FEISHU__APP_SECRET="efN3hVVOajwSITZIfPjRSbnualUBx6eP"

# LLM (家庭内 MLX 服务, 10.10.10.138:8001)
export SPIDE_LLM__LOCAL_API_KEY="ak47"
EOF
chmod 600 /root/.spide/env.sh
```

### 1.6 初始化数据库

```bash
pct exec 107 -- bash -c "
  source /root/.spide/env.sh
  export PATH=/opt/Spide_agent/.venv/bin:\$PATH
  cd /opt/Spide_agent
  python -c \"
import asyncio
from spide.storage.sqlite_repo import SqliteRepository
from spide.storage.models import HotTopic

async def main():
    repo = SqliteRepository(HotTopic, db_path='spide_data.db')
    await repo.start()
    print('[OK] hot_topics table created')
    await repo.stop()

asyncio.run(main())
\"
"
```

### 1.7 安装 Dashboard 启动脚本

```bash
scp scripts/spide-dashboard.service.sh root@10.10.10.10:/tmp/
ssh root@10.10.10.10 "pct push 107 /tmp/spide-dashboard.service.sh /usr/local/bin/spide-dashboard"
ssh root@10.10.10.10 "pct exec 107 -- chmod +x /usr/local/bin/spide-dashboard"
```

### 1.8 启动 Dashboard

```bash
ssh root@10.10.10.10 "pct exec 107 -- spide-dashboard start"
# [OK] Dashboard 已启动 (PID 4940)
#      端点: http://0.0.0.0:8765/api/dashboard
```

## 二、PVE 宿主机 Nginx 反代

### 2.1 安装 Nginx

```bash
ssh root@10.10.10.10
apt install -y nginx openssl
```

### 2.2 生成自签 ECC 证书（10 年有效）

```bash
mkdir -p /etc/nginx/ssl
cd /etc/nginx/ssl
openssl ecparam -genkey -name prime256v1 -out spide.key
openssl req -new -x509 -key spide.key -out spide.crt -days 3650 \
  -subj '/C=CN/ST=Beijing/L=Beijing/O=SpideHarness/CN=spide.local' \
  -addext 'subjectAltName=DNS:spide.local,DNS:localhost,IP:10.10.10.10,IP:10.10.10.16,IP:127.0.0.1'
chmod 600 spide.key
```

### 2.3 部署 Nginx 配置

将 `configs/nginx-spide.conf` 复制到 PVE 宿主机：

```bash
# 在本地 macOS 工作站
scp configs/nginx-spide.conf root@10.10.10.10:/etc/nginx/sites-available/spide

# 在 PVE 宿主机
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/spide /etc/nginx/sites-enabled/spide
nginx -t        # 验证配置
nginx            # 启动
ss -tlnp | grep 8443   # 确认监听
```

### 2.4 端口说明

| 端口 | 用途 | 冲突风险 |
|------|------|----------|
| 80   | 已被 PVE 其他服务占用 | ❌ |
| 443  | 已被 PVE 其他服务占用 | ❌ |
| 8006 | PVE Web 管理（pveproxy）| ❌ 不要动 |
| **8088** | **HTTP 监听（重定向到 8443）** | ✅ |
| **8443** | **HTTPS 监听（反代目标）** | ✅ |

### 2.5 防火墙放行

```bash
# PVE 宿主机（如果启用 ufw/iptables）
iptables -A INPUT -p tcp --dport 8443 -j ACCEPT
ip6tables -A INPUT -p tcp --dport 8443 -j ACCEPT
```

## 三、家庭防火墙端口映射

### 方案 A：IPv6 直连（推荐）

如果家庭防火墙分配了**公网 IPv6**（如 `2001:db8::abcd`）：

```
[飞书] → 公网 IPv6:443 → [防火墙 DNAT] → 10.10.10.10:8443
```

防火墙规则示例（iptables）：
```bash
ip6tables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 \
  -d 2001:db8::abcd \
  -j DNAT --to-destination [10.10.10.10]:8443
```

### 方案 B：IPv4 端口映射

如果家庭防火墙有公网 IPv4：
```
[飞书] → 公网 IPv4:443 → [防火墙 DNAT] → 10.10.10.10:8443
```

## 四、飞书开发者后台配置

### 4.1 启用事件订阅

1. 访问 https://open.feishu.cn/app/cli_a976c6aaaa7adcbb/event-subscriptions
2. 添加事件订阅：
   - **请求 URL**：`https://[你的公网地址]:443/api/feishu/event`
     （注意：公网是 443，但内部转发到 8443；飞书连接到你的公网 443）
   - **加密策略**：推荐选择 "TLS 1.2 及以上" + 上传自签证书 / 选择 "不加密"（HTTP）做首次测试
3. 验证 Token：留空（已在代码中跳过）
4. 订阅事件：`im.message.receive_v1`（接收消息 v2.0）

### 4.2 添加机器人能力

1. 应用功能 → 机器人 → 启用
2. 权限管理 → 消息与群组：
   - `im:message` - 接收消息
   - `im:message.group_at_msg` - 接收群@消息
   - `im:message.p2p_msg` - 接收私聊
   - `im:message:send_as_bot` - 以应用身份发消息

### 4.3 发布应用

1. 版本管理与发布 → 创建版本 → 提交审核
2. 企业自用应用可"申请内测"或"申请发布"

### 4.4 测试

在飞书中向机器人发送：
```
crawl weibo
```

应该看到富文本卡片回复。

## 五、故障排查

### 5.1 502 Bad Gateway

**症状**：Nginx 返回 502

**排查**：
```bash
# 1. 检查 CT107 Dashboard 是否运行
ssh root@10.10.10.10 "pct exec 107 -- spide-dashboard status"

# 2. 从 PVE 宿主机直接访问 CT107
curl http://10.10.10.16:8765/api/dashboard

# 3. 检查 Nginx 错误日志
tail -f /var/log/nginx/spide.error.log
```

### 5.2 飞书事件 URL 验证失败

**症状**：飞书后台 "请求 URL 不合法"

**排查**：
```bash
# 1. 测试公网可达性（用手机 4G 访问）
curl -k https://[公网地址]:443/api/feishu/event

# 2. 查看飞书错误码
# 错误码 200 = 成功
# 错误码 401 = 签名验证失败
# 错误码 500 = 服务器内部错误

# 3. 检查 CT107 日志
ssh root@10.10.10.10 "pct exec 107 -- tail -50 /var/log/spide/dashboard.log"
```

### 5.3 LLM 慢 / 超时

**症状**：Agent 响应 1-3 分钟

**原因**：家庭内 MLX 服务 CPU 推理速度约 0.15 tokens/s

**缓解**：
- 缩短 LLM 输出长度（`max_tokens=512`）
- 优化提示词减少对话轮次
- 启用 `_fallback_keyword()` 关键词降级（已实现）

### 5.4 PVE 宿主机端口被占用

```bash
# 查看 80/443 谁在占用
lsof -i :80
lsof -i :443

# 停止 PVE 自带 nginx（注意：可能影响 PVE 镜像源代理）
# 推荐: 不停,改用 8088/8443
```

## 六、备份与恢复

```bash
# 备份
ssh root@10.10.10.10 "pct exec 107 -- tar -czf /tmp/spide_backup.tar.gz \
  /opt/Spide_agent/spide_data.db \
  /opt/Spide_agent/.venv \
  /root/.spide"
pct pull 107 /tmp/spide_backup.tar.gz /tmp/

# 恢复
pct push 107 /tmp/spide_backup.tar.gz /tmp/spide_backup.tar.gz
ssh root@10.10.10.10 "pct exec 107 -- bash -c '
  cd / && tar -xzf /tmp/spide_backup.tar.gz
'"
```

## 七、参考链接

- **飞书事件订阅文档**：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-api-event-subscription
- **Nginx 反向代理文档**：https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- **PVE LXC 容器**：https://pve.proxmox.com/wiki/Linux_Container
