# TASK-003 SQLite 数据层与幂等写入

- 编号：TASK-003
- 里程碑：v0.1.0
- 前置依赖：TASK-001
- 优先级：🔴 P0
- 状态：✅ done
- 来源：architecture.md 模块 B、ADR-003
- 关联文档：api-contract.md「数据产物契约」

## 执行步骤

1. 设计并落地表结构：`raw_topics`、`raw_videos`、`raw_comments`、`raw_danmaku`、`raw_subtitles`、`videos`、`scores`、`cards`、`crawl_state`
2. 建立 `schema_version` 表与简单迁移机制（按版本号顺序执行 SQL）
3. 实现通用 upsert：以 BV 号 / 主键去重，重复执行不产生重复行
4. 实现采集状态表 `crawl_state`：记录每个关键词 / 每个视频的采集状态与时间，支持断点续采
5. 开启 WAL 模式与外键约束
6. 提供只读查询辅助函数，供后续评分模块使用

## 验收标准（布尔判定）

- [ ] 初始化命令可重复执行，不报错、不重复建表
- [ ] 同一视频连续写入两次，表中仍只有一行且字段为最新值
- [ ] `crawl_state` 能区分 `pending` / `done` / `failed` 三种状态
- [ ] 数据文件位于 `data/bilitube.db`，路径可配置
- [ ] 单元测试全部通过，不依赖网络

## 评测方案

- 单元测试：建库、迁移幂等、upsert 覆盖、状态流转
- 数据校验：用 `sqlite3` 检查表结构与索引是否存在
- 回归：删除数据库文件后重新初始化，流程可正常重跑
