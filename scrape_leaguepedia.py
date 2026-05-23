#!/usr/bin/env python
"""从 Leaguepedia 增量抓取比赛数据并保存到 SQLite。

注意：本脚本不会自动运行，需手动执行。
已入库的比赛（external_id）不会重复请求后续页。

示例:
  python scrape_leaguepedia.py --new-limit 30
  python scrape_leaguepedia.py --where "Tournament LIKE '%%LPL%%2025%%'" --new-limit 50
"""

from __future__ import annotations

import argparse
import logging
import sys

from scraper.cache import MatchCache
from scraper.leaguepedia import (
    DEFAULT_MAX_DELAY,
    DEFAULT_MAX_PAGES,
    DEFAULT_MIN_DELAY,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RATE_LIMIT_PAUSE,
    LeaguepediaError,
    LeaguepediaScraper,
)
from scraper.store import save_games


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Leaguepedia 比赛数据爬虫（手动运行，增量抓取）",
    )
    parser.add_argument(
        "--new-limit",
        type=int,
        default=30,
        help="最多抓取并保存的新比赛条数（默认 30）",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="API 起始偏移量",
    )
    parser.add_argument(
        "--where",
        type=str,
        default=None,
        help=r"Cargo WHERE 条件，如 Tournament LIKE '%%LCK%%2025%%'",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"最多请求 API 页数上限（默认 {DEFAULT_MAX_PAGES}）",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"每页条数（默认 {DEFAULT_PAGE_SIZE}，最大 500）",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY,
        help=f"请求前最小随机等待秒数（默认 {DEFAULT_MIN_DELAY}）",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY,
        help=f"请求前最大随机等待秒数（默认 {DEFAULT_MAX_DELAY}）",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="失败/限流时最大重试次数（默认 5）",
    )
    parser.add_argument(
        "--rate-limit-pause",
        type=float,
        default=DEFAULT_RATE_LIMIT_PAUSE,
        help=f"遇到 429 时基础暂停秒数，逐次递增（默认 {DEFAULT_RATE_LIMIT_PAUSE}）",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="保存时不跳过已存在的 external_id（仍会利用缓存减少 API 请求）",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="输出详细日志",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.min_delay > args.max_delay:
        print("错误: --min-delay 不能大于 --max-delay", file=sys.stderr)
        return 1

    cache = MatchCache()
    known = cache.load_from_db()
    print(f">>> 缓存已加载: 数据库中已有 {known} 场比赛")

    scraper = LeaguepediaScraper(
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        max_retries=args.max_retries,
        rate_limit_pause=args.rate_limit_pause,
        page_size=min(args.page_size, 500),
    )

    print(">>> 开始增量抓取（仅新比赛）...")
    if args.where:
        print(f"    筛选: {args.where}")
    print(
        f"    目标新比赛 <= {args.new_limit} 条 | "
        f"随机等待 {args.min_delay}~{args.max_delay}s | "
        f"最多 {args.max_pages} 页"
    )

    try:
        rows, fetch_stats = scraper.fetch_new_games(
            cache,
            new_limit=args.new_limit,
            offset=args.offset,
            where=args.where,
            max_pages=args.max_pages,
        )
    except LeaguepediaError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"网络或解析错误: {exc}", file=sys.stderr)
        return 1

    print(
        f">>> API 请求 {fetch_stats.api_requests} 次, "
        f"拉取 {fetch_stats.rows_from_api} 条, "
        f"新比赛 {fetch_stats.new_rows} 条 "
        f"({fetch_stats.stopped_reason})"
    )

    if not rows:
        print(">>> 没有新比赛需要保存")
        return 0

    stats = save_games(rows, cache, skip_existing=not args.no_skip)
    print(
        f">>> 入库: 新增 {stats['inserted']} 条, "
        f"跳过 {stats['skipped']} 条, 失败 {stats['failed']} 条"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
