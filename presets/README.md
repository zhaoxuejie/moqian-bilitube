# presets

配方（preset）：**「按什么标准跑」**。代码只认目录结构，不认识里面的具体内容。

```
presets/<name>/
├── preset.json    名称、版本、说明，以及下面各文件的名字
├── keywords.txt   采集关键词，每行一个，# 开头为注释
├── rules.json     过滤规则：词表、分区白名单、时长门槛、单 UP 配额
├── scoring.json   打分权重、时长分桶、小样本阈值
└── prompt.md      生成卡片的 system prompt
```

## 现有配方

| 目录 | 用途 |
| --- | --- |
| `ai-video/` | 线上在用的真实配方（20 个关键词、48 个 AI 词、5 个信号加权） |
| `example/` | 最小示例，用来演示结构；换成播客/论文等其它领域时从这里复制 |

## 怎么用

```bash
python -m bilitube score --preset presets/ai-video
python -m bilitube card  --preset presets/ai-video
python -m bilitube collect search --preset presets/example --max-pages 1
python -m bilitube filter --preset presets/example
```

不传 `--preset` 时默认 `presets/ai-video`。`--keywords` / `--rules` 可以临时覆盖单个文件。

## 怎么新建一个

```bash
cp -r presets/example presets/podcast
# 改 keywords.txt / rules.json / scoring.json / prompt.md，再改 preset.json 里的 name 与 version
python -m bilitube score --preset presets/podcast
```

## 写作约定

- **`scoring.json` 的权重之和必须是 1.0**（加载时会校验，容差 0.01）
- `weights` 的键只能取引擎认识的信号：`fav_rate` / `coin_rate` / `like_rate` / `talk_rate` / `log_view`；
  **可以只用其中几个**（`example/` 就只用了三个），没写的信号不参与打分
- `buckets` 是有序区间 `[起点秒, 终点秒, 标签]`，最后一段终点写 `null` 表示无上限；
  同一分区、同一时长档内的视频才互相比较分位
- `prompt.md` 必须要求模型输出同一套 JSON 字段，否则卡片解析会失败
- `version` 会出现在日志里（`ai-video@v1`），调参后建议升一版，方便回溯"这条分是哪版配方打的"

## 关于公开

`ai-video/` 是真实配方（关键词、词表、权重、prompt 都是调出来的），
已经写进仓库根目录的 `.gitignore`，**不再进版本库**——本地文件还在，命令照常跑。

```gitignore
/presets/ai-video/
```

- 公开仓库只保留 `example/` 这个骨架
- 它曾经在历史里（`849654f`），所以对外发布必须用**新历史**，不能直接推这个仓库的 log
- 新克隆后要跑流水线：`--preset presets/example`，或者
  `cp -r presets/example presets/ai-video` 再把自己的配方填进去
