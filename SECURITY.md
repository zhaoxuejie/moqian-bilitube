# SECURITY

## 报告问题

- 优先用 GitHub 的私密漏洞报告（Security → Advisories → Report a vulnerability）
- 也可以提 issue，但**不要公开贴出可直接利用的细节**
- 如果涉及站点数据（某个 BV 号被错误收录、隐私信息），同样走上面的渠道

## 不要提交的东西

本仓库是公开的，提交前确认没有把下面这些带进来：

| 不要提交 | 说明 |
| --- | --- |
| `.env` | 含 `LLM_API_KEY`、`BILI_SESSDATA`，已在 `.gitignore` |
| `data/` | 本地 SQLite 与采集报告（含全量弹幕），已在 `.gitignore` |
| `presets/ai-video/` | 真实配方，已在 `.gitignore`，仓库只留 `example/` |

## 已知边界

- 站点是纯静态的，没有后端、没有账号体系，攻击面主要是前端与第三方嵌入
- 详情页嵌入 B 站官方播放器，用户访问时会连接 `bilibili.com`（见站点「隐私与免责」页）
- 流水线会访问 B 站接口，限速 0.8 请求/秒；不要为了跑得更快而调高，容易触发风控
