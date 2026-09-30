# Repository Guidelines

## 项目测试约束

创建或初始化项目级 `AGENTS.md` 时，必须将本节放在文件顶部，紧随文件标题之后，并置于其他项目规则之前。

### 基本原则

- 测试强度必须与变更的实际风险相匹配，不得机械地为每一次修改运行测试。
- 仅当修改影响运行逻辑、外部可观察行为、数据结果、接口契约或关键配置时，才运行相应的行为测试。
- 没有行为变化时，不运行行为测试；存在行为变化时，只验证受影响的部分；完整端到端测试仅用于最终验收。

### 测试设计

- 优先在编写实现代码之前明确验收标准、可能的失败方式和测试方案。
- 当后续发现新的缺陷、边界情况或回归风险时，允许补充相应测试。
- 对重要的用户操作流程、核心业务流程和复杂的跨系统行为，将端到端测试作为主要验收机制。
- 当单元测试或集成测试能够更快速、更稳定地验证独立逻辑或系统边界时，可以使用有针对性的单元测试或集成测试。
- 在对系统进行隔离测试之前，先记录已知及合理可预见的失败方式，再围绕这些失败方式设计实现和测试。

### 非行为变更

对于下列不影响程序行为的修改，不运行单元测试、集成测试或端到端测试：

- 内部变量重命名。
- 注释、说明文字和界面文案调整。
- 文档修改。
- 代码格式化。
- 不改变语义的导入顺序、展示顺序或内容顺序调整。
- 不影响执行结果的代码整理和机械性修改。

对于非行为变更，只进行必要的最小验证，例如：

- 检查修改差异。
- 确认变量或符号引用已完整更新。
- 确认配置文件能够正常解析。
- 运行必要的静态检查。
- 没有适用的自动验证方式时，仅审查修改差异。

不得为了体现“已经验证”而运行与当前变更无关的测试。

如果变量名、字段名或顺序属于公共接口、配置键、环境变量、数据库结构、数据协议、规则优先级或任务执行流程的一部分，则不视为非行为变更，应根据实际影响进行针对性测试。

### 开发与最终验证

- 开发期间，只运行与当前修改直接相关的测试和端到端场景。
- 开发期间不运行完整的端到端测试套件，也不反复执行高成本的全量验证。
- 完整的端到端测试套件只在进入最终验证阶段后运行。
- 如果最终验证失败，应先定位并修复问题，再重新运行受影响的测试；只有在必要时才重新运行完整端到端测试。
- 最终端到端验证必须生成可复现、可核验的工件，例如测试报告、执行轨迹、截图集、录制结果、结果包或带校验和的数据产物。

## Project Structure & Module Organization

- `backend/app/`: FastAPI routes, schemas, models, providers, ingestion services, and storage; tests live in `backend/tests/`.
- `frontend/src/`: React components, API client, shared types, styles, and offline map assets (`assets/china.json`).
- `worker/app/worker.py`: scheduled refresh using backend services. `docker-compose.yml` wires API, worker, static web, and PostgreSQL; `pyproject.toml` and `uv.lock` manage Python dependencies.

## Build, Test, and Development Commands

- `cp .env.example .env`: initialize local configuration.
- `docker compose up --build -d`: build and start all services.
- `./dev.sh`: start native API/worker and Vite; `DEV_BACKEND=docker ./dev.sh` uses containers. Web runs at `http://localhost:5173`.
- `./dev-stop.sh`: stop project processes; Docker mode also stops Compose containers.
- `cd frontend && npm ci`: install dependencies; `npm run build` checks TypeScript and builds assets.
- `uv sync --frozen` installs Python 3.12 dependencies; `uv run pytest backend/tests/test_cma_bulletins.py` verifies disclosure parsing.

## Coding Style & Naming Conventions

Use four-space Python indentation, type hints, and `snake_case`; use two-space TypeScript indentation, double quotes, semicolons, `camelCase`, and `PascalCase` component filenames. TypeScript uses strict mode. No formatter or linter is configured. Keep provider integration behind `backend/app/providers/` and configuration in `core/config.py`.

## Testing Guidelines

Backend tests use pytest conventions and FastAPI `TestClient`; name files `test_*.py` and functions `test_*`. Pytest is provided by the uv dev group. No frontend test runner or coverage threshold is configured. For affected provider changes, cover failures and mock fallback. Final acceptance uses `scripts/acceptance.py`, API reports, and browser screenshots.

## Commit & Pull Request Guidelines

History uses short, free-form English/Chinese subjects, such as `change vite port`. Prefer scoped, imperative subjects, e.g. `fix: handle provider timeouts`. PRs should state behavior, validation, related issues, and configuration changes; include screenshots for UI changes. Follow `RULES.md`: update `README.md`, `SESSION_STATE.md`, and `DECISIONS.md` for behavior changes.

## Security & Configuration Tips

Keep credentials in ignored `.env`; update `.env.example` without secrets. Configure warning and forecast providers separately. Disable silent production mock fallback with `FALLBACK_TO_MOCK_ON_FAILURE=false`; preserve warning sources and AI confidence.
