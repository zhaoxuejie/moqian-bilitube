# 部署与发版

维护者文档。README 只讲怎么在本地跑起来，这里记录线上运维：

- 生产环境是什么、怎么配
- 发版流程（tag → 自动部署）
- 常见故障的排查顺序

## 生产环境

站点是纯静态产物（`web/out`），部署在 **Cloudflare Workers 静态资源**。
选型理由见 [architecture.md](architecture.md) 的 ADR-020。

- 线上地址：<https://www.51bilitube.com>（apex 与 www 均已绑定）
- `web/wrangler.toml` 声明 `out/` 为静态资源目录，404 走 `404.html`，
  目录式路径自动映射 `index.html`
- 缓存与安全头写在 `web/public/_headers`

Cloudflare 项目（Workers Builds）的配置：

| 配置项 | 值 |
| ---- | ---- |
| 构建命令 | `cd web && npm ci && npm run build` |
| 部署命令 | `cd web && npx wrangler deploy` |
| 环境变量 | `NODE_VERSION=20` |
| 生产分支 | `release` |

## 分支与部署的关系

**生产分支是 `release`，不是 `main`。**

| 动作 | 结果 |
| ---- | ---- |
| `git push origin main` | 只进仓库，**不构建** |
| 推一个 `vX.Y.Z` 的 tag | 自动发版（见下） |
| `powershell -File scripts/update.ps1 -Deploy` | 手动发版，等价于推 tag |
| `powershell -File scripts/update.ps1 -Push` | 只提交数据并推 main，不部署 |

## 发版

```bash
# 1. 把 CHANGELOG 的 [Unreleased] 整理成新版本段落
# 2. 打 tag 并推送
git tag -a v0.3.1 -m "本次改动说明"
git push origin v0.3.1
```

`.github/workflows/release.yml` 会依次执行：

1. 校验 tag 命名必须是 `vX.Y.Z`
2. **闸门一**：tag 指向的提交必须在 `main` 上——防止在功能分支打 tag 误部署
3. **闸门二**：必须相对线上是快进——防止给旧提交补 tag 把站点回退
4. 通过后 `git push origin HEAD:release` → Cloudflare 构建部署（约 2–3 分钟）
5. 创建 GitHub Release，说明由 GitHub 按提交自动生成

任何一道闸门不过，工作流直接失败，**不会部署**，线上保持原版本。

## 换域名

只改 `web/lib/site.ts` 里的 `SITE.url` 一行，canonical、`robots.txt` 的 Host、
`sitemap.xml` 的 1,362 条 URL 会一起切换。

## 排查顺序

### push 了但没部署

1. 确认推的是 `release` 分支（或按上面的 tag 流程）
2. 查 Cloudflare 构建状态：

   ```bash
   curl -s "https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/builds/workers/<SCRIPT_TAG>/builds" \
     -H "Authorization: Bearer <API_TOKEN>" | jq '.result[0]'
   ```

3. 如果构建记录里根本没有这个提交，检查 Git 连接指向：

   ```bash
   curl -s "https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/builds/workers/<SCRIPT_TAG>" \
     -H "Authorization: Bearer <API_TOKEN>" | jq '.result.git_repository'
   ```

   `repo_id` 必须是本仓库。**曾经踩过它指向另一个仓库、于是 push 永远不触发构建的坑。**

### 构建失败

| 报错 | 原因 | 解法 |
| ---- | ---- | ---- |
| `Could not read package.json` | 构建目录不对 | 构建命令写 `cd web && ...`，不要依赖控制台的「根目录」设置 |
| `npm ci` 找不到 lockfile | 同上 | 同上 |
| `Node.js version ... not supported` | Node 太旧 | 环境变量 `NODE_VERSION=20` |

### 站点能开但 SEO 地址是 localhost

`SITE.url` 为空时会回退到 `http://localhost:3000`。填上正式域名重新发版即可。

## 相关

- 站点数据契约：`docs/api-contract.md`
- 端到端人工验证清单：`docs/tasks/task-012-deploy-basics.md`
