"""将爬虫数据写入 SQLite（复用 Flask 应用配置）。"""

from __future__ import annotations

from app import create_app, db
from app.models import Match
from scraper.cache import MatchCache
from scraper.leaguepedia import LeaguepediaScraper


def save_games(
    rows: list[dict],
    cache: MatchCache,
    *,
    skip_existing: bool = True,
) -> dict[str, int]:
    """
    保存比赛记录，并更新内存缓存。
    返回统计: inserted, skipped, failed
    """
    app = create_app()
    scraper = LeaguepediaScraper()
    stats = {"inserted": 0, "skipped": 0, "failed": 0}

    with app.app_context():
        for row in rows:
            try:
                data = scraper.row_to_match_kwargs(row)
            except ValueError:
                stats["failed"] += 1
                continue

            external_id = data.pop("external_id", None)
            if skip_existing and external_id and cache.contains(external_id):
                stats["skipped"] += 1
                continue

            match = Match(**data, external_id=external_id)
            db.session.add(match)
            stats["inserted"] += 1
            if external_id:
                cache.add(external_id)

        db.session.commit()

    return stats
