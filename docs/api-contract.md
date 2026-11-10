# BiliTube 接口契约文档
当前版本：v1.0.0
关联PRD：prd.md
关联架构：architecture.md

> 约定：
> - 本项目没有运行时 HTTP 服务，契约分三类：**外部接口封装**、**内部模块 CLI**、**数据产物文件**
> - 状态：draft / stable / deprecated
> - deprecated 必须写迁移指引
> - MAJOR 版本不兼容变更，归档旧版本后新建版本文档

## 通用约定

- 基础地址：`https://api.bilibili.com`
- 统一请求头：`User-Agent`（浏览器 UA）、`Referer: https://www.bilibili.com/`
- 网络出口：B 站接口走**直连**（实测 0.4s，无需代理）；代理只用于 GitHub / npm 等外部依赖
- 账号隔离：除字幕外**不携带账号 Cookie**（`SESSDATA`），但会携带匿名设备指纹 `buvid3`/`buvid4`——搜索接口缺它一律 412（ADR-022）；字幕走单独通道，串行、限速 1 req/s、仅对最终入选视频执行
- 限速：单机 1–2 req/s，失败指数退避，命中缓存不重采
- 统一返回格式（B 站原生）：

```json
{
  "code": 0,
  "message": "OK",
  "ttl": 1,
  "data": {}
}
```

- 错误码（B 站原生，只列本项目关心的）：

| code | 含义 | 处理 |
| ---- | ---- | ---- |
| 0 | 成功 | 正常处理 |
| -352 | 风控拦截 | 退避重试，超过 3 次标记失败并跳过 |
| -403 | 无权限 | 标记不可用，不重试 |
| -404 | 不存在 | 标记失效，不重试 |
| -412 | 请求被拒 | 降低频率后重试 |

- 鉴权方式：仅字幕接口需要 Cookie（`BILI_SESSDATA`），其余公开接口无需鉴权

## 接口列表

### 外部接口 1：关键词搜索

路径：`GET /x/web-interface/wbi/search/type`
状态：stable
版本：v1

| 参数名 | 类型 | 是否必填 | 说明 |
| ---- | ---- | ---- | ---- |
| search_type | string | 是 | 固定 `video` |
| keyword | string | 是 | 关键词，需 URL 编码 |
| order | string | 否 | `stow` 收藏 / `click` 播放 / `pubdate` 最新 |
| page | int | 否 | 页码，1–50（单关键词上限 1000 条） |

返回要点：`data.result[]`，字段含 `bvid`、`aid`、`title`、`play`、`favorites`、`duration`、`pubdate`、`author`、`mid`。

### 外部接口 2：视频详情

路径：`GET /x/web-interface/view`
状态：stable
版本：v1

| 参数名 | 类型 | 是否必填 | 说明 |
| ---- | ---- | ---- | ---- |
| bvid | string | 是 | 视频 BV 号 |

返回要点：`data.cid`、`data.pubdate`、`data.duration`、`data.tname_v2`、`data.stat.{view,like,coin,favorite,danmaku,reply}`、`data.owner.{mid,name}`。

### 外部接口 3：评论

路径：`GET /x/v2/reply`
状态：stable
版本：v1

| 参数名 | 类型 | 是否必填 | 说明 |
| ---- | ---- | ---- | ---- |
| type | int | 是 | 固定 `1`（视频） |
| oid | int | 是 | 视频 aid |
| pn | int | 否 | 页码 |
| ps | int | 否 | 每页条数 |
| sort | int | 否 | `2` 按热度 |

### 外部接口 4：弹幕

路径：`GET /x/v1/dm/list.so`
状态：stable
版本：v1

| 参数名 | 类型 | 是否必填 | 说明 |
| ---- | ---- | ---- | ---- |
| oid | int | 是 | 视频 cid，返回 deflate 压缩 XML |

### 外部接口 5：字幕

路径：`GET /x/player/v2`
状态：draft（覆盖率待验证）
版本：v1

| 参数名 | 类型 | 是否必填 | 说明 |
| ---- | ---- | ---- | ---- |
| bvid | string | 是 | 视频 BV 号 |
| cid | int | 是 | 视频 cid |

> 📌 未登录返回空字幕列表，必须携带 `BILI_SESSDATA`。若 20 条抽样覆盖率低于 30%，本接口降级为可选增强项，第三层评估改用弹幕 + 评论 + 简介。

### 外部接口 6：分区榜单

路径：`GET /x/web-interface/ranking/v2`
状态：stable
版本：v1

| 参数名 | 类型 | 是否必填 | 说明 |
| ---- | ---- | ---- | ---- |
| rid | int | 是 | `188` 科技 / `36` 知识 |
| type | string | 否 | 固定 `all` |

> 📌 `x/web-interface/ranking/region` 已实测只剩 11 条，标记为 deprecated，迁移到本接口。

## 内部模块 CLI 契约

统一入口：`python -m bilitube <command>`，每个命令幂等，可重复执行。

| 命令 | 输入 | 输出 | 说明 |
| ---- | ---- | ---- | ---- |
| `collect search --keywords <file>` | 关键词文件 | `raw_topics` 表 | 按关键词 × 排序方式采集 |
| `collect ranking --rids 188,36` | 分区 id | `raw_topics` 表 | 只采近期榜 |
| `collect enrich --limit N` | `raw_topics` | `raw_videos` 表 | 补详情、评论、弹幕、字幕 |
| `normalize` | `raw_*` | `videos` 表 | 去重、系列合并、失效剔除 |
| `score --stage rules` | `videos` | `scores` 表 | 硬过滤 + 分位归一 |
| `score --stage content` | `videos` | `scores` 表 | LLM 分类与内容打分 |
| `card` | `videos` + `scores` | `cards` 表 | 生成卡片与主题 |
| `export --out <dir>` | 全库 | JSON 分片 + 向量 | 供站点构建 |
| `report` | 全库 | 统计报告 | 覆盖率、通过率、失败清单 |

退出码：`0` 成功、`1` 部分失败（已落库）、`2` 参数错误、`3` 外部接口不可用。

## 数据产物契约

`export` 命令把 SQLite 导出为三个文件，写入 `web/public/data/`，由构建期服务端读取（`lib/data.ts`）：

- `videos.json`：已通过筛选并完成评分的视频数组，按 `scores.total` 倒序
- `topics.json`：主题数组 `[{ "name": "RAG", "count": 309 }]`，取出现次数 ≥3 的前 80 个
- `meta.json`：整批数据的统计口径，供首屏与页脚渲染

`videos.json` 单条结构（与 `lib/types.ts` 的 `Video` 一致）：

```json
{
  "bvid": "BV1xx411c7mD",
  "title": "视频标题",
  "up": "UP 主",
  "mid": 123,
  "duration": 3600,
  "pubdate": 1748000000,
  "tname": "计算机技术",
  "cover": "https://i0.hdslb.com/bfs/archive/xxx.jpg",
  "view": 0,
  "favorite": 0,
  "coin": 0,
  "danmaku": 0,
  "reply": 0,
  "scores": { "machine": 0, "content": 0, "total": 0 },
  "flags": ["low_sample"],
  "card": {
    "summary": "一句话摘要",
    "why": "为什么值得看",
    "audience": "适合谁",
    "prereq": "前置知识",
    "difficulty": 3,
    "freshness": "evergreen",
    "verdict": "教程",
    "quality": 68.8,
    "topics": ["RAG"]
  }
}
```

`meta.json` 结构：

```json
{
  "generated_at": "2026-11-04T18:35:05",
  "videos": 1360,
  "with_cards": 1360,
  "topics": 80,
  "candidates": 3652,
  "danmaku_rows": 209549,
  "covers": 1360
}
```

字段约束：

- `card.freshness` ∈ {`evergreen`, `aging`, `outdated`}
- `card.verdict` ∈ {`教程`, `实战`, `新闻`, `测评`, `搬运`, `水`}，由 LLM 判定，前端只做展示不做分发
- `card.quality` 为 LLM 给出的 0–100 内容分，`scores.content` 与它同源
- `scores` 均为 0–100，`total = 0.6 × machine + 0.4 × content`
- `pubdate` 为 Unix 秒；`cover` 为 https 绝对地址，前端按需追加 `@672w_378h_1c.webp` 尺寸后缀
- `card` 可能为 `null`（历史数据缺卡片），前端必须降级显示
- `meta.covers` 应等于 `meta.videos`，可作为封面回填的验收判据

## 接口变更记录

| 接口 | 变更内容 | 版本 | 关联ADR |
| ---- | ---- | ---- | ---- |
| `ranking/region` | 标记 deprecated，迁移到 `ranking/v2` | v1 | ADR-002 |
| `videos.json` | 新增 `cover`（https 绝对地址），卡片据此渲染封面 | v4 | ADR-015 |
| `meta.json` | 新增 `candidates` / `danmaku_rows` / `covers` 三个统计字段 | v4 | ADR-015 |

## 评审记录

| 评审人 | 时间 | 结论 | 备注 |
| ---- | ---- | ---- | ---- |
| 用户 | — | 待评审 | 初稿 |
