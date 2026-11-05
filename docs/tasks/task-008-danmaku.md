# TASK-008 弹幕采集（仅通过视频）

- 编号：TASK-008
- 里程碑：v0.1.0
- 前置依赖：TASK-006、TASK-007
- 优先级：🔴 P0
- 状态：✅ done
- 来源：prd.md 模块 A F-COL-6 / architecture.md ADR-010
- 关联文档：api-contract.md「外部接口 4」

## 执行步骤

1. 实现 `collect danmaku --limit N --batch-size 100` 子命令
2. 只对 `videos.status = 'passed'` 且 `cid` 非空的视频抓弹幕
3. 弹幕去重写入 `raw_danmaku(bvid, content)`，单视频上限保留前 1200 条
4. 用 `crawl_state` 记录 `danmaku:<bvid>` 的完成状态，支持断点续采
5. 失败记录标记 `failed`，重跑时重试
6. 报告：目标数、完成、失败、入库弹幕条数、平均每视频条数

## 验收标准（布尔判定）

- [ ] 对 100 条通过视频执行，`raw_danmaku` 入库条数 > 0 且视频数 = 100
- [ ] 同一视频重复执行不产生重复弹幕（`UNIQUE(bvid, content)` 生效）
- [ ] 中断后重跑只处理剩余视频
- [ ] 失败视频状态为 `failed` 且可重试
- [ ] 单元测试覆盖成功、去重、断点三种场景

## 评测方案

- 单元测试：mock 弹幕接口
- 真实 smoke：3 条视频，核对弹幕条数与接口返回一致
- 数据校验：`SELECT COUNT(DISTINCT bvid) FROM raw_danmaku` 与报告一致
