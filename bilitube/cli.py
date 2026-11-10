"""命令行入口：解析参数、装配配置与日志、分发子命令。"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from .collector import (
    collect_danmaku,
    collect_enrich,
    collect_search,
    open_connection,
    read_keywords,
    summarize,
    summarize_danmaku,
    summarize_enrich,
)
from .config import Config
from .filter import apply_filter, load_rules
from .filter import summarize as summarize_filter
from .export import export_site
from .export import summarize as summarize_export
from .http import BiliClient
from .llm import LlmClient, run_cards
from .llm import summarize as summarize_cards
from .logging import setup_logging
from .preset import DEFAULT_PRESET_PATH, PresetError, load_preset
from .scoring import score_all
from .scoring import summarize as summarize_score

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_USAGE = 2
EXIT_EXTERNAL = 3

PLACEHOLDER_COMMANDS = ("normalize", "report")


def build_parser() -> argparse.ArgumentParser:
    # 子命令也接受 --data-dir / --log-level；用 SUPPRESS 兜底避免覆盖主解析器的值
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", default=argparse.SUPPRESS, help="数据目录，默认 data")
    common.add_argument("--log-level", default=argparse.SUPPRESS, help="日志级别，默认 INFO")
    common.add_argument("--preset", type=Path, default=argparse.SUPPRESS, help="配方目录")

    parser = argparse.ArgumentParser(
        prog="bilitube",
        description="B 站 AI 大模型视频精选流水线",
    )
    parser.add_argument("--data-dir", default=None, help="数据目录，默认 data")
    parser.add_argument("--log-level", default=None, help="日志级别，默认 INFO")
    parser.add_argument(
        "--preset",
        type=Path,
        default=None,
        help=f"配方目录，默认 {DEFAULT_PRESET_PATH}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    collect = subparsers.add_parser("collect", parents=[common], help="采集 B 站数据")
    collect_sub = collect.add_subparsers(
        dest="collect_action", required=True, metavar="<action>"
    )
    search = collect_sub.add_parser("search", parents=[common], help="按关键词分页采集")
    search.add_argument(
        "--keywords",
        type=Path,
        default=None,
        help="关键词文件；不填则用配方里的 keywords.txt",
    )
    search.add_argument(
        "--fresh",
        action="store_true",
        help="忽略断点状态强制重抓（周更增量用；bvid 幂等，不会重复）",
    )
    search.add_argument("--max-pages", type=int, default=50, help="每个关键词每轮最多抓多少页")
    search.add_argument("--page-size", type=int, default=20, help="每页条数")
    search.add_argument("--orders", default="stow,click", help="排序方式，逗号分隔")
    search.add_argument("--limit-keywords", type=int, default=None, help="只取前 N 个关键词")

    enrich = collect_sub.add_parser("enrich", parents=[common], help="补齐视频详情与 UP 粉丝")
    enrich.add_argument("--limit", type=int, default=None, help="本次最多补多少条")
    enrich.add_argument("--batch-size", type=int, default=100, help="每多少条打印一次进度")

    filter_cmd = subparsers.add_parser("filter", parents=[common], help="按规则过滤候选池")
    filter_cmd.add_argument(
        "--rules", type=Path, default=None, help="规则文件；不填则用配方里的 rules.json"
    )

    subparsers.add_parser("score", parents=[common], help="分位归一与机器评分")

    danmaku = collect_sub.add_parser("danmaku", parents=[common], help="抓取通过视频的弹幕")
    danmaku.add_argument("--limit", type=int, default=None, help="本次最多处理多少条")
    danmaku.add_argument("--batch-size", type=int, default=100, help="每多少条打印一次进度")

    card_cmd = subparsers.add_parser("card", parents=[common], help="LLM 生成卡片与内容分")
    card_cmd.add_argument("--limit", type=int, default=None, help="本次最多处理多少条")
    card_cmd.add_argument("--model", default=None, help="覆盖 LLM_MODEL")
    card_cmd.add_argument("--batch-size", type=int, default=20, help="每多少条打印一次进度")

    update_cmd = subparsers.add_parser(
        "update", parents=[common], help="增量更新：采集 → 补齐 → 过滤 → 评分 → 弹幕 → 卡片 → 导出"
    )
    update_cmd.add_argument("--max-pages", type=int, default=3, help="每个关键词每排序抓多少页")
    update_cmd.add_argument("--orders", default="pubdate", help="排序方式，默认按发布时间")
    update_cmd.add_argument("--resume", action="store_true", help="沿用断点状态（默认强制重抓）")
    update_cmd.add_argument("--limit-enrich", type=int, default=None, help="本次最多补齐多少条")
    update_cmd.add_argument("--limit-danmaku", type=int, default=None, help="本次最多抓多少条弹幕")
    update_cmd.add_argument("--limit-cards", type=int, default=None, help="本次最多生成多少张卡片")
    update_cmd.add_argument("--skip-cards", action="store_true", help="跳过卡片生成")
    update_cmd.add_argument(
        "--out", type=Path, default=Path("web/public/data"), help="导出目录"
    )

    export_cmd = subparsers.add_parser("export", parents=[common], help="导出站点 JSON")
    export_cmd.add_argument(
        "--out", type=Path, default=Path("web/public/data"), help="输出目录"
    )

    for name in PLACEHOLDER_COMMANDS:
        subparsers.add_parser(name, parents=[common], help=f"{name} 子命令")

    return parser


def _make_client(config: Config, logger):
    """构造带设备指纹的客户端。

    B 站搜索接口对没有 buvid 的请求直接 412，所以先 warmup 一次；
    失败不阻断，只是风控概率更高。
    """
    client = BiliClient(
        rate_limit_rps=config.rate_limit_rps,
        timeout=config.request_timeout,
        sessdata=config.bili_sessdata,
    )

    if client.warmup():
        logger.info("已获取匿名设备指纹（buvid3/buvid4）")
    else:
        logger.warning("未能获取设备指纹，请求将不带 buvid，极易触发 412")
    return client


def _run_collect(args: argparse.Namespace, config: Config, logger) -> int:
    if args.max_pages < 1:
        logger.error("--max-pages 必须 >= 1")
        return EXIT_USAGE

    if args.keywords:
        keywords = read_keywords(Path(args.keywords))
        source = str(args.keywords)
    else:
        try:
            preset = load_preset(args.preset or DEFAULT_PRESET_PATH)
        except PresetError as exc:
            logger.error("%s", exc)
            return EXIT_USAGE
        keywords = list(preset.keywords)
        source = f"{preset.path}/keywords.txt（配方 {preset.label}）"

    if args.limit_keywords:
        keywords = keywords[: args.limit_keywords]
    if not keywords:
        logger.error("关键词为空: %s", source)
        return EXIT_USAGE

    orders = tuple(item.strip() for item in args.orders.split(",") if item.strip())
    if not orders:
        logger.error("--orders 不能为空")
        return EXIT_USAGE

    logger.info("开始采集：关键词 %d 个，排序 %s，最多 %d 页", len(keywords), orders, args.max_pages)

    conn = open_connection(config.db_path)
    client = _make_client(config, logger)

    try:
        report = collect_search(
            client,
            conn,
            keywords,
            orders=orders,
            max_pages=args.max_pages,
            page_size=args.page_size,
            report_dir=config.data_dir / "reports",
            fresh=bool(getattr(args, "fresh", False)),
        )
    finally:
        client.close()
        conn.close()

    logger.info(summarize(report))
    if report.failed_pages:
        logger.warning("失败页：%s", report.failed_pages)
        return EXIT_PARTIAL
    return EXIT_OK


def _run_enrich(args: argparse.Namespace, config: Config, logger) -> int:
    conn = open_connection(config.db_path)
    client = _make_client(config, logger)

    try:
        report = collect_enrich(
            client,
            conn,
            limit=args.limit,
            batch_size=args.batch_size,
            report_dir=config.data_dir / "reports",
        )
    finally:
        client.close()
        conn.close()

    logger.info(summarize_enrich(report))
    if report.failed_items:
        logger.warning("失败条目：%s", report.failed_items[:10])
        return EXIT_PARTIAL
    return EXIT_OK


def _run_danmaku(args: argparse.Namespace, config: Config, logger) -> int:
    conn = open_connection(config.db_path)
    client = _make_client(config, logger)

    try:
        report = collect_danmaku(
            client,
            conn,
            limit=args.limit,
            batch_size=args.batch_size,
            report_dir=config.data_dir / "reports",
        )
    finally:
        client.close()
        conn.close()

    logger.info(summarize_danmaku(report))
    if report.failed_items:
        logger.warning("失败条目：%s", report.failed_items[:10])
        return EXIT_PARTIAL
    return EXIT_OK


def _run_export(args: argparse.Namespace, config: Config, logger) -> int:
    conn = open_connection(config.db_path)
    try:
        report = export_site(conn, Path(args.out))
    finally:
        conn.close()
    logger.info(summarize_export(report))
    return EXIT_OK


def _run_update(args: argparse.Namespace, config: Config, logger) -> int:
    """一条命令跑完增量：采集 → 补齐 → 过滤 → 评分 → 弹幕 → 卡片 → 导出。

    设计：每步都依赖上一步的落库结果，任一步抛错就停下并返回非零，
    已经写进库的部分不会丢，重跑时天然续上。
    """
    import json

    try:
        preset = load_preset(args.preset or DEFAULT_PRESET_PATH)
    except PresetError as exc:
        logger.error("%s", exc)
        return EXIT_USAGE

    orders = tuple(item.strip() for item in args.orders.split(",") if item.strip())
    if not orders:
        logger.error("--orders 不能为空")
        return EXIT_USAGE

    report_dir = config.data_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, object]] = []

    logger.info(
        "增量更新开始：配方 %s，首页 %d 页 × %d 个关键词，排序 %s",
        preset.label,
        args.max_pages,
        len(preset.keywords),
        ",".join(orders),
    )

    conn = open_connection(config.db_path)
    client = _make_client(config, logger)

    try:
        search_report = collect_search(
            client,
            conn,
            list(preset.keywords),
            orders=orders,
            max_pages=args.max_pages,
            report_dir=report_dir,
            fresh=not args.resume,
        )
        steps.append({"step": "search", **search_report.as_dict()})
        logger.info("① 采集：%s", summarize(search_report))
        if search_report.aborted:
            logger.error("触发风控，本次更新中止（已采部分已落库，稍后重跑即可续上）")
            return EXIT_PARTIAL

        enrich_report = collect_enrich(
            client, conn, limit=args.limit_enrich, batch_size=200, report_dir=report_dir
        )
        steps.append({"step": "enrich", **enrich_report.as_dict()})
        logger.info("② 补齐：%s", summarize_enrich(enrich_report))

        rules = load_rules(preset.rules_path)
        filter_report = apply_filter(conn, rules)
        steps.append({"step": "filter", **filter_report.as_dict()})
        logger.info("③ 过滤：%s", summarize_filter(filter_report))

        score_report = score_all(conn, preset)
        steps.append({"step": "score", **score_report.as_dict()})
        logger.info("④ 评分：%s", summarize_score(score_report))

        danmaku_report = collect_danmaku(
            client, conn, limit=args.limit_danmaku, batch_size=200, report_dir=report_dir
        )
        steps.append({"step": "danmaku", **danmaku_report.as_dict()})
        logger.info("⑤ 弹幕：%s", summarize_danmaku(danmaku_report))
    finally:
        client.close()

    try:
        if args.skip_cards:
            logger.info("⑥ 卡片：按参数跳过")
        elif not config.llm_api_key:
            logger.warning("⑥ 卡片：未配置 LLM_API_KEY，跳过")
        else:
            model = config.llm_model
            llm = LlmClient(api_key=config.llm_api_key, base_url=config.llm_base_url, model=model)
            try:
                card_report = run_cards(
                    llm,
                    conn,
                    model=model,
                    limit=args.limit_cards,
                    batch_size=20,
                    report_dir=report_dir,
                    preset=preset,
                )
            finally:
                llm.close()
            steps.append({"step": "card", **card_report.as_dict()})
            logger.info("⑥ 卡片：%s", summarize_cards(card_report))

        export_report = export_site(conn, Path(args.out))
        steps.append({"step": "export", **export_report.as_dict()})
        logger.info("⑦ 导出：%s", summarize_export(export_report))
    finally:
        conn.close()

    (report_dir / "update.json").write_text(
        json.dumps({"preset": preset.label, "steps": steps}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("增量更新结束，明细见 %s", report_dir / "update.json")
    return EXIT_OK


def _run_card(args: argparse.Namespace, config: Config, logger) -> int:
    if not config.llm_api_key:
        logger.error("未配置 LLM_API_KEY，无法生成卡片")
        return EXIT_USAGE
    try:
        preset = load_preset(args.preset or DEFAULT_PRESET_PATH)
    except PresetError as exc:
        logger.error("%s", exc)
        return EXIT_USAGE

    model = args.model or config.llm_model
    logger.info("LLM: %s @ %s，配方 %s", model, config.llm_base_url, preset.label)

    llm = LlmClient(api_key=config.llm_api_key, base_url=config.llm_base_url, model=model)
    conn = open_connection(config.db_path)
    try:
        report = run_cards(
            llm,
            conn,
            model=model,
            limit=args.limit,
            batch_size=args.batch_size,
            report_dir=config.data_dir / "reports",
            preset=preset,
        )
    finally:
        llm.close()
        conn.close()

    logger.info(summarize_cards(report))
    if report.failed_items:
        logger.warning("失败条目：%s", report.failed_items[:10])
        return EXIT_PARTIAL
    return EXIT_OK


def _run_filter(args: argparse.Namespace, config: Config, logger) -> int:
    if args.rules:
        rules_path = Path(args.rules)
    else:
        try:
            preset = load_preset(args.preset or DEFAULT_PRESET_PATH)
        except PresetError as exc:
            logger.error("%s", exc)
            return EXIT_USAGE
        rules_path = preset.rules_path
        logger.info("使用配方 %s 的规则：%s", preset.label, rules_path)
    rules = load_rules(rules_path)
    conn = open_connection(config.db_path)
    try:
        report = apply_filter(conn, rules)
    finally:
        conn.close()
    logger.info(summarize_filter(report))
    report_dir = config.data_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    import json

    (report_dir / "filter.json").write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return EXIT_OK


def _run_score(args: argparse.Namespace, config: Config, logger) -> int:
    import json

    try:
        preset = load_preset(args.preset or DEFAULT_PRESET_PATH)
    except PresetError as exc:
        logger.error("%s", exc)
        return EXIT_USAGE
    logger.info("使用配方 %s：%s", preset.label, preset.path)

    conn = open_connection(config.db_path)
    try:
        report = score_all(conn, preset)
    finally:
        conn.close()

    logger.info(summarize_score(report))
    for item in report.top[:10]:
        logger.info("  %.1f  %s  %s", item["total"], item["bvid"], item["title"][:30])

    report_dir = config.data_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "score.json").write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # 先按命令行/环境变量建立日志，保证配置阶段的告警也能落盘
    bootstrap_dir = Path(args.data_dir or os.getenv("DATA_DIR") or "data")
    bootstrap_level = (args.log_level or os.getenv("LOG_LEVEL") or "INFO").upper()
    logger = setup_logging(bootstrap_dir / "logs", bootstrap_level)

    config = Config.load(logger=logger)
    if args.data_dir:
        config = replace(config, data_dir=Path(args.data_dir))
    if args.log_level:
        config = replace(config, log_level=args.log_level.upper())

    if config.log_dir != bootstrap_dir / "logs" or config.log_level != bootstrap_level:
        logger = setup_logging(config.log_dir, config.log_level)

    logger.info("command=%s data_dir=%s", args.command, config.data_dir)

    if args.command == "collect":
        if args.collect_action == "search":
            return _run_collect(args, config, logger)
        if args.collect_action == "enrich":
            return _run_enrich(args, config, logger)
        return _run_danmaku(args, config, logger)
    if args.command == "filter":
        return _run_filter(args, config, logger)
    if args.command == "score":
        return _run_score(args, config, logger)
    if args.command == "card":
        return _run_card(args, config, logger)
    if args.command == "export":
        return _run_export(args, config, logger)
    if args.command == "update":
        return _run_update(args, config, logger)

    logger.warning("%s 子命令尚未实现（由后续任务卡交付）", args.command)
    return EXIT_PARTIAL


if __name__ == "__main__":
    sys.exit(main())
