# Repository Guidelines

## 总偏好
- 使用中文对话

## 项目结构
- 根目录：`src/` STM32 固件；`backend/` FastAPI 服务；`web/` Vue 前端；`docs/` 文档；`.pio/` 平台构建输出。
- 前端：`web/src` 业务代码，`web/public` 静态资源，构建产物输出到 `web/dist` 并由后端静态托管。
- 后端：`backend/main.py` 入口，`config.py` 配置，`database.py`/`models.py` 数据访问，`.env` 存放数据库等私密配置（未提交）。

## 构建、测试与本地运行
- 前端开发：在 `web/` 执行 `npm run serve` 启动本地热更新；`npm run build` 生成发布包；`npm run build:watch` 监听源码变更自动持续构建。
- 后端运行：在 `backend/` 执行 `python main.py` 启动 FastAPI（需先 `pip install -r requirements.txt`）；默认监听 `8000` 并托管 `web/dist`。
- 后端依赖初始化：`python init_database.py` 初始化 MySQL 数据库结构。

## 代码风格与命名
- 前端：遵循 Vue 3 单文件组件风格，JS/TS 4 空格缩进；组件 PascalCase，文件 kebab-case（如 `data-card.vue`）；使用 ESLint 规则 `plugin:vue/vue3-essential` + `eslint:recommended`（`npm run lint`）。
- 后端：Python 使用 4 空格缩进，模块、文件采用 snake_case；遵循 PEP8，保持异步 API 非阻塞。

## 测试与验证
- 前端：目前未配置单测，建议为关键逻辑增加组件级或端到端测试（可选 Vitest/Cypress）；发布前至少运行 `npm run build` 确认无错误。
- 后端：如添加数据库或接口变更，编写最小可复现脚本或单元测试，确保 `main.py` 启动不报错；建议在本地 MySQL 实例上验证 CRUD。

## 提交与合并
- Commit：保持清晰动词短语（如 `feat: add websocket reconnect log`、`fix: handle udp decode error`）；一次提交聚焦单一变更。
- PR：描述改动目的、范围和测试结果；如涉及前端界面，请附关键截图或说明；链接相关 Issue（如有）。

## 安全与配置
- 不要提交 `.env`、数据库密码或证书；示例配置放置在 `.env.example` 或文档中。
- MySQL 端口、凭据通过环境变量配置；如在公网部署，请限制 UDP/HTTP 暴露范围并启用防火墙。
