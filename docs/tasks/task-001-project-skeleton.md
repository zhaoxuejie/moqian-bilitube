# TASK-001 工程骨架与 CLI 入口

- 编号：TASK-001
- 里程碑：v0.1.0
- 前置依赖：无
- 优先级：🔴 P0
- 状态：✅ done
- 来源：prd.md 模块 A / architecture.md 第 4 节
- 关联文档：api-contract.md「内部模块 CLI 契约」

## 执行步骤

1. 建立 Python 3.12 包结构：`bilitube/`，包含 `__init__.py`、`__main__.py`、`cli.py`、`config.py`、`logging.py`、`db.py`、`http.py`
2. 增加依赖清单（`requirements.txt`：httpx、pydantic、python-dotenv、pytest）
3. 实现配置加载：读取 `.env` 中的 `BILI_SESSDATA`、`LLM_API_KEY`、`DATA_DIR`；缺省值可用，缺失关键项时告警而非崩溃
4. 实现统一日志：同时输出到 stdout 与 `data/logs/`，按天滚动
5. CLI 入口 `python -m bilitube`，注册子命令占位：`collect`、`normalize`、`score`、`card`、`export`、`report`
6. 按契约固定退出码：0 成功、1 部分失败、2 参数错误、3 外部接口不可用

## 验收标准（布尔判定）

- [ ] `python -m bilitube --help` 退出码为 0，且列出全部 6 个子命令
- [ ] 没有 `.env` 时程序不崩溃，打印一条告警并使用默认配置
- [ ] 日志同时写入 stdout 与 `data/logs/`，文件按日期命名
- [ ] 未知子命令时退出码为 2
- [ ] `pytest` 全部通过，且不依赖网络

## 评测方案

- 单元测试：配置文件加载（有 / 无 `.env`）、退出码约定、日志文件生成
- 手动验证：执行 `python -m bilitube --help` 与 `python -m bilitube bogus`，核对退出码
- 回归：CI 的 markdownlint 仍然通过
