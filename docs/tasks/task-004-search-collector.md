# TASK-004 关键词搜索采集与断点续采

- 编号：TASK-004
- 里程碑：v0.1.0
- 前置依赖：TASK-002、TASK-003
- 优先级：🟠 P1
- 状态：🧪 evaluating（自检通过，待评测）
- 来源：prd.md 模块 A F-COL-1、F-COL-4
- 关联文档：api-contract.md「外部接口 1」「内部模块 CLI 契约」

## 执行步骤

1. 提供关键词矩阵文件 `config/keywords.txt`（首批覆盖：大模型、LLM、RAG、Agent、微调、LoRA、SFT、推理加速、vLLM、Transformer、提示词工程、向量数据库、多模态、文生视频、开源模型）
2. 实现 `collect search` 子命令：每个关键词按 `order=stow` 与 `order=click` 各跑一轮，每轮分页采集
3. 单关键词上限 1000 条（50 页），支持 `--max-pages` 限制，便于小样本验证
4. 每页结果写入 `raw_videos`，并更新 `crawl_state`
5. 断点续采：中断后重跑跳过已完成的关键词 + 页码组合
6. 生成采集报告：关键词数、页数、条数、去重后条数、`-352` 比例、失败页清单

## 验收标准（布尔判定）

- [ ] `python -m bilitube collect search --keywords config/keywords.txt --max-pages 1` 能成功入库
- [ ] 同一命令重复执行，`raw_videos` 行数不增加
- [ ] 中断后重跑，不重复采集已完成的页
- [ ] 采集报告包含去重前后条数与 `-352` 比例
- [ ] 单元测试用 mock 覆盖分页、去重、断点三种场景

## 评测方案

- 真实小样：1 个关键词 × 1 页，核对入库条数与接口返回一致
- 幂等验证：连续执行两次，比对行数
- 断点验证：人为中断后重跑，检查 `crawl_state` 中已完成页被跳过
- 报告校验：报告中的失败页清单与实际日志一致
