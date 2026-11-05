# tasks

任务卡目录。任务采用增量拆分模式：**禁止一次性拆解整个里程碑全部任务**；完成一批，再基于当前进度拆解下一批。

状态枚举（索引表与任务卡状态字段统一写成「图标 + 状态词」，看板一眼可辨）：

- ⬜ **todo**：待开始，尚未启动
- 🟡 **doing**：开发进行中
- 👀 **review**：草稿已产出，等待人工审阅确认
- 🧪 **evaluating**：等待或正在评测验收
- ✅ **done**：评测验收通过，已完成
- 🚫 **abandoned**：废弃，不删除文件、不回收编号

优先级（同样写成「图标 + 等级」）：

- 🔴 **P0**：阻塞，最高优先级，必须最先保障
- 🟠 **P1**：核心，本期必须完成
- ⚪ **P2**：可选，可后置到后续迭代

## 任务索引表

| 编号 | 标题 | 里程碑 | 前置依赖 | 优先级 | 状态 | 关联文档 |
| ---- | ---- | ------ | -------- | ------ | ---- | -------- |
| TASK-001 | 工程骨架与 CLI 入口 | v0.1.0 | 无 | 🔴 P0 | ✅ done | prd.md 模块A；api-contract.md CLI 契约 |
| TASK-002 | B 站 HTTP 客户端 | v0.1.0 | TASK-001 | 🔴 P0 | ✅ done | architecture.md ADR-001/007/008；api-contract.md 外部接口 |
| TASK-003 | SQLite 数据层与幂等写入 | v0.1.0 | TASK-001 | 🔴 P0 | ✅ done | architecture.md 模块B、ADR-003 |
| TASK-004 | 关键词搜索采集与断点续采 | v0.1.0 | TASK-002、TASK-003 | 🟠 P1 | 🧪 evaluating | prd.md F-COL-1；api-contract.md 外部接口1 |
| TASK-005 | 详情补齐（enrich） | v0.1.0 | TASK-004 | 🔴 P0 | ✅ done | prd.md F-COL-4；api-contract.md 外部接口2 |
| TASK-006 | 相关性过滤与硬过滤 | v0.1.0 | TASK-005 | 🔴 P0 | ✅ done | prd.md 硬性过滤；ADR-012 |
| TASK-007 | 分位归一与机器评分 | v0.1.0 | TASK-005、TASK-006 | 🔴 P0 | 🧪 evaluating | prd.md 模块C；ADR-002、ADR-009 |
| TASK-008 | 弹幕采集（仅通过视频） | v0.1.0 | TASK-006、TASK-007 | 🔴 P0 | ✅ done | prd.md F-COL-6；ADR-010 |
| TASK-009 | LLM 内容理解与卡片生成 | v0.1.0 | TASK-008 | 🔴 P0 | ✅ done | prd.md 模块C/D；ADR-002、ADR-013 |
| TASK-010 | 站点骨架与精选清单页 | v0.2.0 | TASK-009 | 🟠 P1 | ✅ done | prd.md 模块F；ADR-004 |
| TASK-011 | 站点视觉重做：编辑型版式与封面 | v0.2.0 | TASK-010 | 🟠 P1 | ✅ done | ADR-015、ADR-016；api-contract.md 数据产物契约 |
| TASK-012 | 部署基础设施：元信息、robots、sitemap、404 与缓存头 | v0.3.0 | TASK-011 | 🟠 P1 | 🧪 evaluating | ADR-020；prd.md 模块F |

## 规则

1. 任务存储模式：**一个任务单独一个文件**，不把多个任务混在同一个文件。
   文件命名：`task-00N-short-description.md`，小写 kebab-case。
   本 readme.md 仅做索引看板，**不存放任务详细正文**；执行步骤、验收标准、评测方案全部放在对应任务独立文件内。
2. 必须所有前置依赖状态为 done，才可以启动本任务
3. 每张任务卡必须包含可判定的验收标准与评测方案；评测不通过，不能标记 done
4. 任务编号全局唯一，废弃任务标记 abandoned，不删除文件、不回收编号
5. 新任务草稿必须人工审阅确认后，才正式入库、更新本表
6. 版本归档时，tasks 整体随同 docs 一起快照存入 archive

## 关联

- 任务来源：prd.md、architecture.md、api-contract.md
- 评测资产：tests/ 评估集、单元测试、契约测试
