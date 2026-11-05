# TASK-010 站点骨架与精选清单页

- 编号：TASK-010
- 里程碑：v0.2.0
- 前置依赖：TASK-009
- 优先级：🟠 P1
- 状态：✅ done
- 来源：prd.md 模块 F / architecture.md ADR-004
- 关联文档：api-contract.md「数据产物契约」

## 执行步骤

1. 新建 `web/`：Next.js 15 + TypeScript + 手写 CSS，`output: export`
2. 实现 `export` 命令：从 SQLite 生成 `web/public/data/videos.json` 与 `topics.json`
3. 首页：精选清单，按主题分组，卡片显示标题、UP、时长、难度、一句话理由、时效标签
4. 详情页：B 站播放器 iframe + 完整卡片 + 弹幕摘要
5. 筛选：类型、难度、时长、年份；排序：综合分 / 收藏分位
6. 搜索：客户端关键词匹配（minisearch 或简单包含匹配）
7. 本地收藏与历史（localStorage）
8. 构建产物可静态托管，无运行时后端

## 验收标准（布尔判定）

- [ ] `npm run build` 成功，生成静态产物
- [ ] 首页渲染出全部已评分视频，且按分数倒序
- [ ] 详情页 iframe 能正常播放
- [ ] 筛选与搜索在 1360 条规模下响应 < 500ms
- [ ] 收藏与历史刷新后仍在
- [ ] 移动端宽度下不横向溢出

## 评测方案

- 构建校验：`npm run build` 退出码 0
- 人工验收：首页 / 详情 / 筛选 / 搜索 / 收藏五条路径各走一遍
- 性能：Chrome DevTools 记录首屏与搜索耗时
