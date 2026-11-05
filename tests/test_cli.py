"""CLI 装配：确认 update 子命令与 collect search --fresh 接线正确。"""

from __future__ import annotations

from pathlib import Path

from bilitube.cli import build_parser


def test_update_parser_defaults() -> None:
    args = build_parser().parse_args(["update"])
    assert args.command == "update"
    assert args.max_pages == 3
    assert args.orders == "pubdate"
    assert args.resume is False
    assert args.skip_cards is False
    assert Path(args.out).as_posix() == "web/public/data"


def test_update_parser_accepts_overrides() -> None:
    args = build_parser().parse_args(
        ["update", "--max-pages", "5", "--orders", "pubdate,click", "--resume", "--skip-cards"]
    )
    assert args.max_pages == 5
    assert args.orders == "pubdate,click"
    assert args.resume is True
    assert args.skip_cards is True


def test_search_has_fresh_flag() -> None:
    args = build_parser().parse_args(["collect", "search", "--fresh"])
    assert args.command == "collect"
    assert args.collect_action == "search"
    assert args.fresh is True
    assert args.keywords is None
