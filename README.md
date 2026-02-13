# Weather Alert Watcher

全国极端天气展示看板（V1）。

本仓库已具备从开发到单机上线的完整链路：`web + api + worker + db + redis`。

## 1. 项目概览

### 1.1 当前阶段
- 全栈可运行
- 地图联动与边界高亮可用
- 真实数据源联调待完成

### 1.2 核心能力
1. 全国省级风险地图（离线 GeoJSON）
2. 预警列表与未来 7 天温湿度曲线
3. 多入口位置联动：定位 / 手输经纬度 / 地图点击 / 预警点击
4. 当前省份仅边界高亮（不覆盖风险填充色）
5. 南海诸岛独立 inset 小框展示
6. worker 每 30 分钟刷新数据
7. provider 配置化：`mock / nmc / qweather / openmeteo`

### 1.3 服务与端口
- `web`：前端看板，`5173`
- `api`：后端接口，`8000`
- `worker`：定时刷新任务
- `db`：PostgreSQL，`5432`
- `redis`：Redis，`6379`

---

## 2. 快速开始（本地）

### 2.1 前置条件
1. Docker Desktop（Mac/Windows）或 Docker Engine（Linux）
2. Docker Compose plugin（`docker compose` 命令可用）
3. 可访问 Docker Hub（首次构建需要拉基础镜像）

### 2.2 启动步骤
1. 复制环境变量模板：
```bash
cp .env.example .env
```
2. 启动全栈：
```bash
docker compose up --build -d
```

### 2.3 运行验证
```bash
docker compose ps
curl -I http://localhost:5173
curl -sS http://localhost:8000/api/v1/health
```
期望结果：
1. `web/api/worker/db/redis` 全部 `Up`
2. `http://localhost:5173` 返回 `200 OK`
3. health 返回 `{"status":"ok"}`

### 2.4 首次使用流程
1. 打开 `http://localhost:5173`
2. 在“位置输入”中使用任一方式：
- 浏览器定位
- 手动输入经纬度
- 地图点击省份
3. 观察地图边界高亮与右侧预警列表是否联动
4. 需要手工刷新时点击“更新看板”
5. 通过“一键还原视图”重置地图视角

---

## 3. 配置参考（`.env`）

### 3.1 核心运行配置
- `REFRESH_INTERVAL_MINUTES`：刷新周期（默认 `30`）
- `WARNING_PROVIDER`：`mock | nmc | qweather`
- `FORECAST_PROVIDER`：`mock | openmeteo | qweather`
- `FALLBACK_TO_MOCK_ON_FAILURE`：失败时是否回退 mock

### 3.2 数据源配置
- NMC：`NMC_SOURCE_URLS`（逗号分隔）
- QWeather：`QWEATHER_API_BASE`、`QWEATHER_API_KEY`
- Open-Meteo：`OPENMETEO_API_BASE`

### 3.3 AI 配置
- `AI_PROVIDER`：`none | openai`
- `AI_ENABLED_FOR_NMC`：是否对 NMC 公告启用 AI 辅助解读
- `OPENAI_API_BASE`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AI_CONFIDENCE_THRESHOLD`

### 3.4 默认定位配置
- `DEFAULT_LAT`
- `DEFAULT_LON`
- `DEFAULT_PROVINCE`
- `DEFAULT_LABEL`

### 3.5 开发/生产建议值
| 配置项 | 开发建议 | 生产建议 |
| --- | --- | --- |
| `WARNING_PROVIDER` | `mock` 或 `nmc` | `nmc`/`qweather` |
| `FORECAST_PROVIDER` | `mock` 或 `openmeteo` | `openmeteo`/`qweather` |
| `FALLBACK_TO_MOCK_ON_FAILURE` | `true` | `false` |
| `AI_PROVIDER` | `none` 或 `openai` | `openai`（可选） |

安全要求：
1. 不提交任何真实 token 到仓库
2. 生产必须通过环境变量或密钥系统注入凭证

---

## 4. 单机生产部署（Nginx + Let's Encrypt）

目标拓扑：
- 公网流量 -> Nginx(80/443) -> `web:5173` 与 `api:8000`

### 4.1 服务器准备（Ubuntu 22.04）
```bash
sudo timedatectl set-timezone Asia/Shanghai
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release
```

### 4.2 安装 Docker 与 Compose
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```
重新登录后继续。

### 4.3 部署应用
```bash
git clone <your-repo-url> weather_alert_watcher
cd weather_alert_watcher
cp .env.example .env
# 编辑 .env，填入生产配置与密钥

docker compose up --build -d
```

### 4.4 安装并配置 Nginx
```bash
sudo apt install -y nginx
sudo rm -f /etc/nginx/sites-enabled/default
```

创建 `/etc/nginx/sites-available/weather-alert`：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 20m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:5173/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/weather-alert /etc/nginx/sites-enabled/weather-alert
sudo nginx -t
sudo systemctl reload nginx
```

### 4.5 签发 HTTPS 证书（Let's Encrypt）
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

续期检查：
```bash
sudo certbot renew --dry-run
```

### 4.6 生产验收
```bash
docker compose ps
curl -sS http://127.0.0.1:8000/api/v1/health
curl -I https://your-domain.com
```

---

## 5. 运维手册

### 5.1 常用命令
```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs api --tail=200
docker compose logs web --tail=200
docker compose logs worker --tail=200

# 单服务重建
docker compose up --build -d web
docker compose up --build -d api
docker compose up --build -d worker

# 全量重启
docker compose down
docker compose up --build -d
```

### 5.2 升级流程
1. `git pull`
2. `docker compose up --build -d`
3. 执行健康检查与页面检查

### 5.3 回滚策略
1. 使用上一版本代码（tag/commit）
2. 在该版本目录执行：`docker compose up --build -d`
3. 验证 `health` 与核心页面功能

### 5.4 PostgreSQL 数据备份与恢复
备份：
```bash
docker exec -t weather_alert_watcher-db-1 pg_dump -U weather weather > weather_backup.sql
```
恢复：
```bash
cat weather_backup.sql | docker exec -i weather_alert_watcher-db-1 psql -U weather -d weather
```

---

## 6. 故障排查

### 6.1 Docker Hub EOF / 拉镜像失败
现象：`failed to fetch oauth token` 或 `Head ... EOF`

处理：
1. 重试构建命令
2. 优先单服务重建减少依赖：
```bash
docker compose up --build -d --no-deps web
```
3. 检查网络与 Docker Hub 访问状态

### 6.2 容器命名冲突
现象：`container name ... is already in use`

处理：
```bash
docker compose ps -a
docker compose down
docker compose up --build -d
```

### 6.3 地图渲染异常
典型现象：双南海、边界遮挡、旧样式未更新

处理：
1. 重建前端容器：`docker compose up --build -d --no-deps web`
2. 浏览器强制刷新（Ctrl/Cmd + Shift + R）
3. 检查是否命中旧缓存或旧容器

### 6.4 浏览器定位失败
原因：权限拒绝、系统定位关闭、浏览器策略限制

兜底：手动输入经纬度或直接点击地图省份

---

## 7. 安全与上线检查清单

上线前请逐项确认：
1. `.env` 不含示例弱口令和空 key
2. `FALLBACK_TO_MOCK_ON_FAILURE=false`
3. 仅暴露必要端口（建议公网仅 80/443）
4. HTTPS 强制生效
5. Nginx 配置通过 `nginx -t`
6. `docker compose ps` 全部服务稳定
7. `/api/v1/health` 正常
8. 首页可访问且地图/预警/曲线正常
9. 日志无持续报错
10. 数据备份流程已验证

---

## 8. API 与接口约定

- 健康检查：`GET /api/v1/health`
- 看板数据：`POST /api/v1/dashboard`
- 请求体关键字段：`lat`、`lon`、`province`

本轮文档改造未修改任何接口路径与响应结构。

---

## 9. 文档索引

- `PROJECT.md`：项目目标与范围
- `ARCHITECTURE.md`：技术架构与约束
- `RULES.md`：协作与质量规则
- `SESSION_STATE.md`：当前状态与风险
- `DECISIONS.md`：关键技术决策记录
