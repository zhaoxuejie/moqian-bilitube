# TASK-009 LLM 内容理解与卡片生成

- 编号：TASK-009
- 里程碑：v0.1.0
- 前置依赖：TASK-008
- 优先级：🔴 P0
- 状态：✅ done
- 来源：prd.md 模块 C/D / architecture.md ADR-002、ADR-013
- 关联文档：api-contract.md「数据产物契约」

## 执行步骤

1. 新增 LLM 客户端（OpenAI 兼容协议），读取 `.env` 的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`
2. 构造输入：标题、简介（截断）、分区、时长、采样弹幕（最多 200 条，去重去噪）
3. 强制 JSON 输出，字段：`verdict`（教程/实战/测评/新闻/水/搬运）、`quality`（0–100）、`summary`、`why`、`audience`、`prereq`、`difficulty`（1–5）、`freshness`（evergreen/aging/outdated）、`topics`（数组）
4. 结果写入 `cards` 表与 `scores.content`，并把 `scores.total` 重算为 `0.6 × machine + 0.4 × content`
5. 幂等：已有卡片且模型版本未变的记录跳过；支持 `--limit` 小批量试跑
6. 失败重试 2 次，仍失败标记 `llm_status = failed` 并记录原因
7. 报告：处理数、成功、失败、平均内容分、平均耗时、token 消耗

## 验收标准（布尔判定）

- [ ] 20 条小批量跑通，JSON 解析成功率 ≥ 98%
- [ ] 卡片 9 个字段全部非空且类型正确
- [ ] 内容分 0–100，`total` 按 0.6/0.4 重算正确
- [ ] 重复执行不重复调用 LLM（命中缓存）
- [ ] 人工抽检 20 条，"为什么值得看"与视频内容相符的比例 ≥ 70%
- [ ] 单元测试用 mock LLM，不产生真实费用

## 评测方案

- 单元测试：mock LLM 返回，覆盖成功、非法 JSON、超时重试
- 小批量真跑：20 条，人工阅读卡片质量
- 成本核算：统计 token 用量，外推全量 1360 条的费用
