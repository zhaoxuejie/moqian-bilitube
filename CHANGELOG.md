# Changelog
所有版本变更记录遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/)
版本语义化：MAJOR.MINOR.PATCH
- MAJOR：不兼容破坏性变更
- MINOR：兼容新增功能
- PATCH：兼容bug修复、微调

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [0.5.0] - 2026-11-06

访问统计上线。

### Added

- Cloudflare Web Analytics：无 cookie、不做跨站追踪，只上报页面浏览的聚合数据。
  beacon 手动注入（`web/components/Analytics.tsx`），token 配在 `SITE.analyticsToken`，
  留空则不注入任何脚本
- `docs/deploy.md` 增加「访问统计」一节：开启步骤、token 填哪、改统计方案时要同步隐私文案

### Changed

- 隐私与免责页第 4 条由「没有统计与广告」改为「访问统计（无 cookie）」，
  写明统计方式、数据范围与退出方法

## [0.4.0] - 2026-11-05

面向使用者的文档与联系方式完善。

### Added

- README 重写：居中标题与徽章、首页截图（浅色 / 深色）、三种人的快速开始、
  带注释的目录树、流水线示意
- 页脚社交入口：GitHub、博客、公众号（二维码悬停显示、点击切换，触屏可用）
- 隐私页常显公众号二维码，作为手机端兜底
- `docs/deploy.md`：生产环境配置、release 分支与 tag 发版流程、排查顺序

### Changed

- README 精简：工作原理去掉权重公式只留一段说明；删除「部署」「发版」两节
  （维护者细节移入 `docs/deploy.md`）
- `AGENTS.md` 补充发版流程，便于后续贡献者与 AI 遵循同一约定

### Fixed

- 页脚二维码弹层被 `img { max-width: 100% }` 压成一条竖线：给容器与图片显式宽高

## [0.3.0] - 2026-11-05

开源发布 + 正式上线：站点在 <https://www.51bilitube.com>，部署与发版全自动化。

### Added

- 开源仓库（MIT）：引擎、站点、文档进库，真实配方与数据库留在本地
- 正式域名 `www.51bilitube.com`（apex 与 www 均绑定 Cloudflare 自定义域），
  canonical / robots / sitemap 的 1362 条 URL 一体切换
- 发版自动化 `.github/workflows/release.yml`：推 `vX.Y.Z` tag →
  校验提交在 main 上、校验不回退 → 推进 `release` 分支 → Cloudflare 构建部署 →
  创建 GitHub Release（说明自动生成）
- 联系方式：隐私页与页脚指向 GitHub Issues
- `NOTICE.md`、`SECURITY.md`：数据来源、下架渠道、限速要求、不要提交什么

### Changed

- 部署方式：Cloudflare Workers 静态资源（`web/wrangler.toml` 声明 `out/` 为 assets，
  404 走自定义页，目录式路径自动映射 `index.html`）
- 部署闸门：生产分支从 `main` 改为 `release`——推 `main` 不再构建，发版才部署
- `scripts/update.ps1` 区分三档：`-Push` 只进仓库、`-Deploy` 发版、`-Build` 本地验证

### Fixed

- 构建命令内联 `cd web`：Workers 项目的「根目录」设置在实测中不生效，
  `npm ci` 会跑到仓库根目录而找不到 `package-lock.json`
- `SITE.url` 为空时 canonical、robots 的 Host、sitemap 全部回退到 localhost，
  线上 1362 条 URL 指向错误域名
- Workers Builds 的 Git 连接曾指向别的仓库（`repo_id` 1331580080），导致 push 永不触发构建
- `scripts/update.ps1` 缺 UTF-8 BOM，PowerShell 5.1 按 ANSI 解析导致语法错误

## [0.2.0] - 2026-11-05

视觉重做 + 暗色模式 + 配方解耦 + 持续更新能力。

### Added

- 暗色模式：跟随系统偏好，页头可手动切换并记住选择；首帧前用同步脚本套用，刷新不闪白
- 「隐私与免责」页（`/privacy/`），页脚底部加入口
- 收藏真正可用：首页主题行「我的收藏」+ 详情页收藏按钮，localStorage 存储、跨组件与跨标签页同步
- `update` 子命令：一条命令跑完增量（采集 → 补齐 → 过滤 → 评分 → 弹幕 → 卡片 → 导出）
- `collect search --fresh`：忽略断点状态强制重抓，支撑每周增量（bvid 写入仍幂等）
- `scripts/update.ps1`：周更入口，支持 `-MaxPages` / `-SkipCards` / `-Build`，附计划任务示例
- 配方（preset）机制：`presets/<name>/` 装 keywords / rules / scoring / prompt，
  引擎只认目录结构；新增 `presets/example/` 作为骨架
- 站点图标改为小电视轮廓（SVG mask + useId），新增 `Logo` / `ThemeToggle` 组件

### Changed

- 首页改为编辑型版式：左右分栏首屏、浅翠绿说明面板、整幅头条卡、三列封面网格
- 配色由朱红 / 暖纸改为翠绿 / 浅青白，颜色全部收敛到 `:root` 令牌
- 排序从顶部下拉移到「值得花时间的内容」右侧，改为平铺文字页签；条数与清除筛选并入标题行
- 分页重做为页码条（固定首末页、断档省略号），翻页后跳转修正到列表顶部
- 详情页右栏：评分条 2px → 4px、补弹幕数、分数两位小数、圆角与标签层级统一
- 页脚重构：与方法区共用 320px + 3 列网格、四栏分工、补底部 baseline 行
- 吸顶导航高度抽成 `--header-h` 令牌（64px），锚点留白与侧栏吸顶改为 calc 联动
- 真实配方移出版本库（`.gitignore` 掉 `presets/ai-video/`），公开仓只保留 `example/`

### Fixed

- `.hero` / `.detail` 用 `padding` 简写，把 `.shell` 的左右内边距清零，导致这两块内容比页头左移 32px
- `score_all` 重跑会把 card 阶段算出的内容分写成 NULL；改为 `COALESCE` 保留并按 0.6/0.4 重算总分
- 「我的收藏」与主题筛选可同时生效，导致空结果且页面上没有退出入口
- 页头「主题」锚点失效（`#topics` 的 id 在改版时丢失）
- markdownlint 把配方的 `prompt.md` 当文档检查（新增 `.markdownlintignore`）

### Removed

- `config/keywords.txt`、`config/rules.json`（内容移入 `presets/ai-video/`）
- `previews-lab/`、`previews-colorways/`（设计定稿后移除，仍可在历史中取回）
## [0.1.0] - 2026-11-05

首个对外版本。内部里程碑 v0.1.0（数据流水线）与 v0.2.0（静态站点）合并为这一次发布。

### Added

- 采集链路：关键词搜索分页、详情补齐、弹幕抓取，全部幂等、可断点续采
- SQLite 数据层（schema v4）：版本化迁移、风控退避计数、UP 粉丝缓存、封面列回填
- 规则化硬过滤：分区白名单、时长门槛、标题党与课程贩售词表、单 UP 配额
- 分区 × 时长档的分位打分；小样本组退化为全站分位并打 `low_sample` 标记
- LLM 卡片：类型判定、摘要、为什么值得看、适合谁、前置知识、难度、时效、主题
- 静态站点：编辑型首屏 + 编辑首选头条 + 三列封面网格；详情页播放器、评分双条、
  编辑手记、同主题推荐
- 页码条分页、主题筛选（`?topic=` 可分享）、`/` 聚焦搜索、本地收藏
- 两套设计预览：`previews-lab/`（四套版式）与 `previews-colorways/`（15 套配色）

### Changed

- 站点配色由朱红 / 暖纸改为翠绿 / 浅青白，颜色全部收敛到 `:root` 令牌，
  换肤只需改一处；封面占位、骨架屏、时长角标、播放器底色也一并令牌化
- 卡片补充 16:9 封面，直连 B 站图床并声明 `no-referrer` 绕过防盗链
- 首页数据改为客户端按需加载，首屏 HTML 从 515 KB 降到 5.5 KB

### Fixed

- `.hero` / `.detail` 使用 `padding` 简写，把 `.shell` 的左右内边距清零，
  导致首屏与详情页比页头、卡片整体左移 32px
- 搜索接口返回 `v_voucher` 风控挑战时被当成空页，导致整页关键字被误标为采完
- `upsert_videos` 会用空值覆盖已补齐的详情字段（改为 `COALESCE`）
- 标题中的 HTML 实体（`&amp;`）未还原，影响标题与主题统计
- 客户端组件误引用服务端模块，导致 Next.js 构建失败
