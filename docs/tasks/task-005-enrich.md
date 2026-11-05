# TASK-005 详情补齐（enrich）

- 编号：TASK-005
- 里程碑：v0.1.0
- 前置依赖：TASK-004
- 优先级：🔴 P0
- 状态：✅ done
- 来源：prd.md 模块 A F-COL-4 / architecture.md ADR-012
- 关联文档：api-contract.md「外部接口 2」

## 执行步骤

1. 数据库迁移 v2：`raw_videos` 增加 `cid`、`tname_v2`、`videos`、`description`、`owner_mid`、`enrich_status`、`enrich_error`、`enriched_at`；新增 `raw_ups` 表
2. 实现 `collect enrich --limit N --batch-size 100` 子命令
3. 调用视频详情接口，补齐分区、投币数、真实统计、分P数、简介
4. **详情响应整份写入 `raw_json`**（覆盖搜索条目），未来新增字段可直接从库内复原，不必重拉
5. 按 `mid` 去重补 UP 主粉丝数（独立接口），结果写入 `raw_ups` 缓存
6. 已 `done` 的记录不再请求；`failed` 的记录重跑时自动重试
7. 风控策略：连续 10 次可重试失败才整体中止，单条失败不阻塞
8. 生成补齐报告：待补 / 完成 / 失败 / 新增粉丝数 / 缓存命中 / 风控比例

## 验收标准（布尔判定）

- [ ] 对 5 个候选执行后，`coin`、`cid`、`description` 均非空
- [ ] `raw_json` 含完整详情（`pages`、`stat`、`owner` 均可读到）
- [ ] 同一 UP 的多个视频，粉丝数接口只被调用一次
- [ ] 重复执行同一命令，请求数为 0
- [ ] 中途中断后重跑，只补齐剩余记录
- [ ] 失败记录状态为 `failed` 且重跑会重试
- [ ] 连续 10 次可重试失败时整体中止，不足 10 次则继续
- [ ] 单元测试全部通过且不联网（mock 客户端）

## 评测方案

- 单元测试：mock 详情与粉丝接口，覆盖成功、失败、去重、限流中止四种分支
- 真实 smoke：5 条候选，核对补齐前后字段差异
- 数据校验：`enrich_stats` 统计与报告数字一致
