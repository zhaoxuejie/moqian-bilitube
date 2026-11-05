# moqian-bilitube

B 站 AI 大模型视频的「值不值得看」决策层：从海量 AI 视频里筛出真正有价值的教程、实战与测评，给出结构化卡片与反算法排序。

## 版本信息

当前版本：v0.2.0（视觉重做、暗色模式、配方解耦、持续更新）

## 概述

B 站首页的推荐按完播率与停留时长优化，容易奖励标题党与合集拼凑。本项目反过来：用三层评估（机器信号 → 文本理解 → 内容理解）判断一条视频"值不值得花两小时"，把结果压成卡片——讲了什么、适合谁、需要什么前置、是否过时——并按内容密度排序，而不是按播放量。

只覆盖 AI 大模型方向：教程课程、实战工程、工具测评。数据来自 B 站公开接口，站点纯静态，无账号、无后端。

当前产出：3652 个候选 → 1360 个通过过滤 → 全部完成弹幕采集与卡片生成。

## 快速启动

> 前置依赖：Python 3.12、Node 20+

1. 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
npm --prefix web install
```

1. 配置环境变量

```bash
copy .env.example .env
# 填入 LLM_API_KEY（必填）；BILI_SESSDATA 选填，仅字幕用
```

1. 跑流水线

```bash
python -m bilitube collect search --preset presets/ai-video --max-pages 10
python -m bilitube collect enrich
python -m bilitube filter
python -m bilitube score
python -m bilitube collect danmaku
python -m bilitube card
python -m bilitube export --out web/public/data
```

1. 构建站点

```bash
npm --prefix web run build      # 产物在 web/out/
python -m http.server 4173 --directory web/out   # 本地预览 http://127.0.0.1:4173
```

## 命令行

| 命令 | 作用 |
| ---- | ---- |
| `collect search` | 按关键词分页采集候选视频 |
| `collect enrich` | 补详情与 UP 粉丝数（按 mid 去重） |
| `collect danmaku` | 抓通过视频的弹幕 |
| `filter` | 规则化硬过滤（词表/分区/时长/UP 配额） |
| `score` | 分区 × 时长档分位归一，产出机器分 |
| `card` | LLM 生成卡片与内容分，重算综合分 |
| `update` | 一条命令跑完增量：采集 → 补齐 → 过滤 → 评分 → 弹幕 → 卡片 → 导出 |
| `export` | 导出站点 JSON |

所有命令幂等、可断点续跑。

## 配方（preset）

「怎么跑」在代码里，「按什么标准跑」在配方里。一个配方就是一个目录：

```text
presets/ai-video/
├── preset.json    名称、版本、各文件名
├── keywords.txt   采集关键词
├── rules.json     过滤规则（词表 / 分区白名单 / 时长门槛 / 单 UP 配额）
├── scoring.json   打分权重、时长分桶、小样本阈值
└── prompt.md      生成卡片的 system prompt
```

```bash
python -m bilitube score --preset presets/ai-video
python -m bilitube card  --preset presets/ai-video
```

不传 `--preset` 时默认用 `presets/ai-video`。换一个领域就是新写一个目录，
不需要改 Python；`--keywords` / `--rules` 仍可用于临时覆盖。

## 持续更新

每周一行命令跑完增量：

```bash
python -m bilitube update --max-pages 3
npm --prefix web run build
```

`update` 会依次执行：按发布时间抓最近几页 → 补齐新视频详情 → 重跑规则 →
重算分位 → 抓新视频弹幕 → 只为缺卡片的生成 → 导出 JSON。

几个关键点：

- **`--fresh` 默认开着**（加 `--resume` 可关掉）。`collect search` 的断点状态是永久的，
  不加 `--fresh` 上周标记过的页会被永久跳过，抓不到新内容
- **每一步都是增量的**：补齐只看 `enrich_status != done`，弹幕只看没有记录的，
  卡片只看「没有卡片」或「模型变了」的
- **评分是全量重算的**：分位是相对值，新视频进来后老视频的分数会小幅变化
- 触发风控（412/429）会自动中止，已采部分已落库，稍后重跑即可续上
- 每步的明细写到 `data/reports/update.json`

### 建议的节奏

| 频率 | 命令 | 耗时 / 成本 |
| ---- | ---- | ---- |
| 每周 | `update --max-pages 3` | 约 15 分钟、< ¥0.5 |
| 每月 | `update --max-pages 10`（扫得更深） | 约 40 分钟、约 ¥1 |
| 每季度 | 人工清理失效视频与主题词表 | 1 小时 |

## 部署

站点是纯静态产物（`web/out`），托管在 Cloudflare Pages（选型见 ADR-020）。

| 配置项 | 值 |
| ---- | ---- |
| Root directory | `web` |
| Build command | `npm ci && npm run build` |
| Output directory | `out` |
| 环境变量 | `NODE_VERSION=20` |

两种接入方式都支持：

- **Pages 项目**：框架预设留空，输出目录填 `out`
- **Workers 项目**（`wrangler deploy`）：已经提供 `web/wrangler.toml`，
  声明 `out/` 为静态资源目录，404 走 `404.html`，目录式路径自动映射 `index.html`

上线前把 `web/lib/site.ts` 里的 `SITE.url` 填成自定义域名，否则 canonical、sitemap、robots
都会指向 localhost。

周更一条命令：`powershell -File scripts/update.ps1 -Build -Push` —— 跑流水线、构建、
提交数据快照并推送，Cloudflare Pages 收到 push 后自动重建。

### 备份

数据库里最贵的是弹幕与卡片，重建要 1 小时加 1 美元：

```bash
python -c "import sqlite3;c=sqlite3.connect('data/bilitube.db');c.execute(\"VACUUM INTO 'data/backup-2026-11-05.db'\")"
```

`presets/ai-video/` 是真实配方，已被 `.gitignore` 排除（只留在本地）。
新克隆的仓库用 `--preset presets/example`，或复制一份 example 后填自己的配方。

## 目录概览

```text
moqian-bilitube/
├── bilitube/            # Python 流水线（采集/过滤/评分/卡片/导出）
├── presets/             # 配方：关键词、过滤规则、打分权重、生成提示词
├── web/                 # Next.js 静态站点
├── data/                # 本地 SQLite 与报告（gitignore）
├── docs/                # PRD、架构、接口契约、任务卡、实测报告
├── tests/               # 单元测试（全部离线）
└── .github/workflows/   # CI：markdownlint、shellcheck、pytest
```

## 规范

- 贡献规范：见 `CONTRIBUTING.md`
- AI 开发约束：见 `AGENTS.md`
- 版本变更记录：见 `CHANGELOG.md`
