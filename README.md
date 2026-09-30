# Weather Alert Watcher

全国极端天气看板：官方预警、CMA 公开消息和位置温湿度预报。

## 数据与展示边界

- CMA 消息复用相邻 `cma_publish` 项目的公开来源、并发抓取和失败隔离思路，采集实现完整保存在本仓库；运行与构建不依赖相邻目录，不读取其私密设置，也不发送邮件。
- 公告保留原文 URL、发布时间、抓取时间、省份和天气主题。正文来自中央气象台页面的 `.writing`，排除导航、页脚和脚本。
- 天气公报、官方预警发布、预警解除、风险预报、中期展望分别展示；`mid-range` 只作为展望。主题标签表示原文涉及内容，可能包含回顾或“无影响”等表述，不能作为省级实时风险判断。
- 地图采用官方标题或正文首段发布语句中的明确颜色与发布时间；联合风险按正文明确带颜色的区域分配，不能把标题最高颜色推广到所有省份。原文披露预报范围时按地区截止过滤，`expires_at` 表示原文预报覆盖截止，不是官方解除时间；未披露时仅展示近 24 小时发布。解除、取消和历史过期产品不进入地图。
- 来源扩展为 22 个全国产品页面：公报、12 类灾害预警、山洪/地质/中小河流洪水/渍涝风险、强对流和森林火险。
- 地方信号通过 NMC 官网查询页使用的公开分页索引单独采集，检查页数、数量、重复与链接。完整快照成功后才替换；失败保留旧快照并显示异常。索引未提供完整有效/解除状态，省市县标题和原文链接保留，不能作为全省统一风险或全部当前有效预警清单。
- 公告默认保留近 72 小时，每个来源展示最新版本。缺少发布时间时明确标注，不能进入正式预警。来源失败保留窗口内已有数据，不生成模拟公告。
- 默认使用真实 CMA + Open-Meteo，关闭模拟回退。预报严格匹配请求坐标；缺失时显示空态。切换位置可按需采集并缓存该位置预报。
- `CMA_BULLETINS_ENABLED=false` 仅关闭公告入库和展示；`WARNING_PROVIDER=cma` 仍独立采集正式预警。公告开启时复用该轮采集结果，避免重复请求；来源失败保留已有预警，不回退到模拟 CMA 预警。

## 项目结构

```text
backend/app/
  api/                 HTTP 接口与响应组装
  core/                环境配置与数据库连接
  models/              预警、预报、公告和刷新状态
  providers/           CMA 正文解析与第三方数据适配
  services/            公告刷新、预报缓存、独立链路编排
  storage/             持久化与保留窗口
backend/tests/         解析、失败隔离、持久化和 API 契约测试
frontend/src/          React 组件、类型、API client、共享位置与时间工具
worker/app/worker.py   周期刷新与 --once 单次采集
scripts/acceptance.py  可复现的真实 API/数据验收
pyproject.toml         Python 依赖真源
uv.lock                锁定依赖
frontend/nginx.conf    静态资源与同源 API 代理
```

## 本机开发

前置条件：`uv`、Node.js 22；Docker 模式另需 Docker Desktop。

```bash
cp .env.example .env   # 已有配置不要覆盖
./dev.sh
```

`dev.sh` 默认运行本机 API + worker + Vite，无需 Docker。Python 使用项目 `.venv`；SQLite 默认路径为仓库内 `weather.db`。日志保存在 `.run/api.log`、`.run/worker.log`，终止脚本会清理本次启动的进程。

```bash
./dev-stop.sh
DEV_BACKEND=docker ./dev.sh       # PostgreSQL/API/worker 容器 + 本机 Vite
DEV_BACKEND=docker ./dev-stop.sh
```

切换两种模式前先停止原环境。前端依赖首次由脚本 `npm ci` 安装；锁文件变更后重新执行 `cd frontend && npm ci`。第三方访问需要代理时，在运行脚本的 shell 设置 `HTTP_PROXY`、`HTTPS_PROXY`，并将本地地址加入 `NO_PROXY`。

单独运行：

```bash
uv sync --frozen
PYTHONPATH=backend uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend uv run python -m worker.app.worker --once
cd frontend && npm run dev
```

API 启动只初始化数据库结构，不抓取外网；定时刷新在 worker 中。首次启动应运行 worker，以获得公告和全国预警。前端读取请求会按需获取所选坐标的预报。

## Docker 部署

```bash
cp .env.example .env   # 仅首次
# 生产须修改 POSTGRES_PASSWORD；已有数据库须保持其既有凭证
# WARNING_PROVIDER=cma, FORECAST_PROVIDER=openmeteo
# FALLBACK_TO_MOCK_ON_FAILURE=false
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:8000/api/v1/ready
```

看板：[http://localhost:5173](http://localhost:5173)。web 使用 Nginx 托管编译后的静态文件，保留 `/api/v1` 路径转发 API。API 与 worker 共用锁定依赖镜像，以非 root 用户运行；数据库、API、web 和 worker 分别有健康检查。

Compose 项目名保持 `weather_alert_watcher`，沿用 `weather_alert_watcher_pg_data` 卷。数据库只在容器网络开放；移除了当前未使用的 Redis。API 和 web 默认仅绑定本机。**不要执行 `docker compose down -v`，该命令会删除数据卷。**

```bash
docker compose logs --tail 100 worker api
docker compose exec worker python -m worker.app.worker --once
docker compose build api web       # 更新依赖或代码
docker compose up -d --force-recreate api worker web
docker compose down                # 保留数据库卷
```

公网部署时，在服务器 Nginx 上配置域名和 TLS，然后将整个站点反代到 `http://127.0.0.1:5173`；容器 web 已负责 `/api/` 转发，不需要剥掉 `/api` 前缀。仅开放 80/443。`deploy/nginx-site.conf` 提供 HTTP 入口示例，再用站点实际域名配置证书。

升级前保存既有镜像标记与数据库备份。回滚使用上一版本代码/镜像重新启动 API、worker、web，并复验健康检查及页面。新增 `bulletin_records` 表不重写既有表结构，回滚时可以保留它。

```bash
docker compose exec -T db pg_dump -U weather weather > weather-backup.sql
# 恢复只在明确选择要覆盖的数据库时执行
```

## 配置

`.env.example` 是公开模板；`.env` 不提交。密钥、代理凭证、生产数据库密码通过环境变量注入，不写入源码或日志。

| 配置项 | 默认值 / 含义 |
| --- | --- |
| `WARNING_PROVIDER` | `cma`；另支持 `qweather`、`nmc`、`mock` |
| `FORECAST_PROVIDER` | `openmeteo`；另支持 `qweather`、`mock` |
| `CMA_BULLETINS_ENABLED` | `true`，独立公告链路开关 |
| `CMA_SOURCE_URLS` | 5 个基础公报来源；台风旧 URL 归一化去重 |
| `CMA_WARNING_SOURCE_URLS` | 新增全国灾害预警/风险产品，与基础来源合并；空值关闭补充源 |
| `CMA_LOCAL_SIGNALS_ENABLED` | `true`，地方预警索引独立开关 |
| `CMA_LOCAL_SOURCE_URL` | 已验证的 NMC 官网查询地址，非有稳定性承诺的正式接口 |
| `CMA_LOCAL_MAX_PAGES` | `30`，每页请求 100 条；超限报错，不静默截断 |
| `BULLETIN_RETENTION_HOURS` | `72`，公告保留窗口 |
| `REFRESH_INTERVAL_MINUTES` | `30`，worker 刷新与预报缓存间隔 |
| `FALLBACK_TO_MOCK_ON_FAILURE` | `false`；开发演示可开，UI 显示演示标识 |
| `HTTP_TIMEOUT_SECONDS` | `20`，每次外部请求的超时 |
| `POSTGRES_PASSWORD` | 本机模板 `weather`，生产须更换为 URL 安全字符组成的密码 |
| `WEB_BIND/WEB_PORT/API_PORT` | `127.0.0.1/5173/8000` |
| `CORS_ORIGINS` | 本机 Vite 来源列表；生产同源代理无需放开全部来源 |

公告采集不使用 LLM。既有 AI 配置仅为扩展接口保留，不能用模型生成的颜色替代官方预警颜色。CMA/NMC 来源仅允许中央气象台域名；新增网页模板须补充正文与发布时间的解析验证。图片内容不做 OCR，不能从图片猜测等级。

## 验证

按 `AGENTS.md` 的风险约束选择受影响测试；文档改动不运行行为测试。开发中的例子：

```bash
uv run pytest backend/tests/test_cma_bulletins.py -q
uv run pytest backend/tests/test_data_pipeline.py -q
uv run pytest backend/tests/test_ingestion_switches.py -q
uv run pytest backend/tests/test_cma_warning_accuracy.py backend/tests/test_cma_local_signals.py -q
cd frontend && npm run build
docker compose config --quiet
```

最终验收：

```bash
uv run pytest --junitxml=artifacts/validation/backend-tests.xml
uv run python scripts/acceptance.py
PYTHONPATH=backend uv run python scripts/cma_audit.py
# 原始官方样本离线重放，冻结样本时刻
PYTHONPATH=backend uv run python scripts/cma_audit.py --offline artifacts/cma-audit --as-of 2026-09-30T06:30:00+00:00 --output artifacts/cma-audit/replay
```

验收脚本验证静态部署、数据库就绪、CMA 来源和时间、北京/四川真实预报，以及没有模拟数据；保存 API 样本、时间戳报告与 SHA-256。浏览器另验证省份联动、公告筛选、原文摘录、空态和移动端布局，并保存截图。容器健康表示进程或数据库可用，数据是否及时以看板来源状态为准。官方核查结论、遗漏边界与补充数据方向见 [CMA 核查报告](docs/cma-warning-audit.md)。当前 30 分钟轮询不是即时发布通道，可按需求调整 `REFRESH_INTERVAL_MINUTES`；正式预警生命周期和空间落区应接入经授权的结构化数据服务。

## API

- `GET /api/v1/health`：进程存活。
- `GET /api/v1/ready`：数据库可访问。
- `POST /api/v1/dashboard`：请求 `lat`、`lon`、可选 `province/address`，返回全国预警、公告、当前坐标预报和逐来源刷新状态。

响应在原字段上增加 `bulletins`、`source_statuses`、`forecast_source`、`forecast_location`；时间统一携带 UTC 时区，UI 使用北京时间。

## 文档

`PROJECT.md` 描述范围；`ARCHITECTURE.md` 描述组件边界；`RULES.md` 描述协作规则；`DECISIONS.md` 记录决策；`SESSION_STATE.md` 记录当前验证结果。实施范围与失败方式见 `docs/cma-dashboard-plan.md`。
