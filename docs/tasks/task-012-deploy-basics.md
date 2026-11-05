# TASK-012 部署基础设施：站点元信息、robots、sitemap、404 与缓存头

- 编号：TASK-012
- 里程碑：v0.3.0
- 前置依赖：TASK-011（✅ done）
- 优先级：🟠 P1
- 状态：✅ done
- 关联文档：architecture.md ADR-020；prd.md 模块F

## 背景

站点是 `output: "export"` 的纯静态产物（1364 页 + 1.37MB JSON），准备托管在 Cloudflare Pages。
`*.pages.dev` 在国内无法直连，正式访问走自定义域名，因此构建期需要知道站点 origin。
当前缺 `metadataBase`、robots、sitemap、404 与缓存策略，部署后会出现四类问题：

1. 分享链接没有预览卡片（OG 图是相对路径，解析不到）
2. 搜索引擎几乎不收录 1360 个详情页
3. 打开不存在的 BV 号落到默认英文 404
4. 每次访问都全量拉 1.37MB 数据 JSON

## 范围

1. `web/lib/site.ts`：增加 `url` 与 `SITE_ORIGIN`（留空回退 localhost），导出标题与描述常量
2. `web/app/layout.tsx`：`metadataBase`、OpenGraph、Twitter Card、canonical、keywords
3. `web/app/v/[bvid]/page.tsx`：`generateMetadata` —— 每条视频独立 title/description/canonical，
   用封面当分享图（`http://` 升级为 `https://`）
4. `web/app/privacy/page.tsx`：canonical
5. 新增 `web/app/robots.ts`、`web/app/sitemap.ts`（静态导出下生成 `robots.txt` / `sitemap.xml`）
6. 新增 `web/app/not-found.tsx` 自定义 404
7. 新增 `web/public/_headers`（Cloudflare Pages 缓存与安全头）
8. 新增 `scripts/gen-og.py` 与 `web/public/og.png`（1200×630 分享图）
9. `scripts/update.ps1` 增加 `-Push`：数据有变化时提交 `web/public/data` 并推送

## 不做

- 不改数据流水线、不改站点视觉
- 不引入第三方统计（Cloudflare Web Analytics 需在控制台开启，属于部署阶段操作）
- 不提交域名、凭据等私有信息

## 验收标准（布尔）

- [ ] `npm run build` 后 `out/` 中存在 `robots.txt`、`sitemap.xml`、`og.png`、`404.html`、`_headers`
- [ ] `sitemap.xml` 的 `<url>` 数量 = 视频数 + 2（首页与隐私页）
- [ ] 首页 HTML 含 `og:image`、`og:title`、`twitter:card`、`<link rel="canonical">`
- [ ] 详情页 HTML 的 canonical 指向 `/v/<bvid>/`，`og:title` 为该视频标题
- [ ] `SITE.url` 为空时构建成功且全部降级到 localhost（本地开发不受影响）
- [ ] `scripts/update.ps1 -Push` 在数据无变化时不产生空提交
- [ ] `pytest` 与 `markdownlint` 通过

## 评测方案

- 构建后脚本断言上述文件存在、`<url>` 计数正确、关键 meta 片段存在（离线，无需域名）
- 部署后人工验证：分享链接有卡片、`/sitemap.xml` 可访问、404 页为中文

## 部署信息（供 TASK-013 使用）

| 配置项 | 值 |
| --- | --- |
| 平台 | Cloudflare Pages |
| Root directory | `web` |
| Build command | `npm ci && npm run build` |
| Output directory | `out` |
| 环境变量 | `NODE_VERSION=20` |
