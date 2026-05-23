"""系列赛缓存：已入库的系列赛ID不再重复请求/写入。"""

from __future__ import annotations

from app import create_app, db
from app.models import Series


class SeriesCache:
    """从 SQLite 加载已知的系列赛 external_id。"""

    def __init__(self) -> None:
        self._known_ids: set[str] = set()

    def load_from_db(self) -> int:
        app = create_app()
        with app.app_context():
            rows = (
                db.session.query(Series.external_id)
                .filter(Series.external_id.isnot(None))
                .all()
            )
            self._known_ids = {row[0] for row in rows if row[0]}
        return len(self._known_ids)

    def contains(self, series_id: str | None) -> bool:
        if not series_id:
            return False
        return series_id.strip() in self._known_ids

    def add(self, series_id: str) -> None:
        if series_id:
            self._known_ids.add(series_id.strip())

    @property
    def size(self) -> int:
        return len(self._known_ids)
