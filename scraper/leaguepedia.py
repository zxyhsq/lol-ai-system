"""Leaguepedia Cargo API 爬虫 — 抓取比赛数据并写入 SQLite。"""

from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import requests

from scraper.cache import MatchCache

logger = logging.getLogger(__name__)

API_URL = "https://lol.fandom.com/api.php"
TABLE = "ScoreboardGames"
FIELDS = [
    "GameId",
    "Tournament",
    "Team1",
    "Team2",
    "Team1Score",
    "Team2Score",
    "Winner",
    "DateTime_UTC",
    "Patch",
]

# 模拟常见浏览器 User-Agent（每次 Session 随机选一个）
USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
)

DEFAULT_MIN_DELAY = 2.0
DEFAULT_MAX_DELAY = 5.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_RATE_LIMIT_PAUSE = 60.0
DEFAULT_PAGE_SIZE = 20
DEFAULT_MAX_PAGES = 30

KNOWN_LEAGUES = (
    "LPL",
    "LCK",
    "LEC",
    "LCS",
    "LCP",
    "LTA",
    "MSI",
    "Worlds",
    "PCS",
    "VCS",
    "CBLOL",
    "LJL",
    "LLA",
    "LCO",
    "TCL",
    "LFL",
    "NACL",
    "LTA North",
    "LTA South",
)


class LeaguepediaError(Exception):
    pass


class RateLimitError(LeaguepediaError):
    """API 返回 429 / ratelimited。"""


@dataclass
class FetchStats:
    api_requests: int = 0
    pages_fetched: int = 0
    rows_from_api: int = 0
    new_rows: int = 0
    stopped_reason: str = ""


@dataclass
class LeaguepediaScraper:
    min_delay: float = DEFAULT_MIN_DELAY
    max_delay: float = DEFAULT_MAX_DELAY
    max_retries: int = DEFAULT_MAX_RETRIES
    rate_limit_pause: float = DEFAULT_RATE_LIMIT_PAUSE
    page_size: int = DEFAULT_PAGE_SIZE
    timeout: int = 30
    session: requests.Session = field(default_factory=requests.Session, init=False)

    def __post_init__(self) -> None:
        ua = random.choice(USER_AGENTS)
        self.session.headers.update(
            {
                "User-Agent": ua,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://lol.fandom.com/",
            }
        )
        logger.info("User-Agent: %s", ua[:60] + "...")

    def _sleep_random(self) -> float:
        """每次 API 请求前随机等待，避免短时间大量请求。"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug("等待 %.1f 秒后继续 ...", delay)
        time.sleep(delay)
        return delay

    def _pause_rate_limit(self, attempt: int) -> None:
        pause = self.rate_limit_pause * attempt
        logger.warning("触发限流，暂停 %.0f 秒后重试 (第 %d 次) ...", pause, attempt)
        time.sleep(pause)

    def fetch_new_games(
        self,
        cache: MatchCache,
        *,
        new_limit: int = 50,
        offset: int = 0,
        where: str | None = None,
        order_by: str = "DateTime_UTC DESC",
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> tuple[list[dict[str, Any]], FetchStats]:
        """
        仅拉取数据库中不存在的新比赛。
        按时间倒序分页；若整页均已缓存则提前停止，减少 API 调用。
        """
        stats = FetchStats()
        page_size = min(self.page_size, 500)
        collected: list[dict[str, Any]] = []
        current_offset = offset

        while len(collected) < new_limit and stats.pages_fetched < max_pages:
            batch = self._cargo_query(
                limit=page_size,
                offset=current_offset,
                where=where,
                order_by=order_by,
            )
            stats.api_requests += 1
            stats.pages_fetched += 1

            if not batch:
                stats.stopped_reason = "api_empty"
                break

            stats.rows_from_api += len(batch)

            if cache.page_fully_cached(batch):
                stats.stopped_reason = "all_cached"
                logger.info("本页比赛均已缓存，停止请求（offset=%d）", current_offset)
                break

            new_batch = cache.filter_new_rows(batch)
            if new_batch:
                need = new_limit - len(collected)
                collected.extend(new_batch[:need])

            if len(batch) < page_size:
                stats.stopped_reason = "api_exhausted"
                break

            current_offset += page_size

        stats.new_rows = len(collected)
        if not stats.stopped_reason:
            stats.stopped_reason = "new_limit_reached" if len(collected) >= new_limit else "max_pages"

        return collected[:new_limit], stats

    def _cargo_query(
        self,
        *,
        limit: int,
        offset: int,
        where: str | None,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "action": "cargoquery",
            "format": "json",
            "tables": TABLE,
            "fields": ",".join(FIELDS),
            "limit": limit,
            "offset": offset,
        }
        if where:
            params["where"] = where
        if order_by:
            params["order_by"] = order_by

        url = f"{API_URL}?{urlencode(params)}"
        data = self._request_json(url)
        rows = data.get("cargoquery") or []
        return [item.get("title", {}) for item in rows]

    def _request_json(self, url: str) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            self._sleep_random()

            try:
                resp = self.session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                wait = min(30, 3 * attempt)
                logger.warning("网络错误: %s，%d 秒后重试 (%d/%d)", exc, wait, attempt, self.max_retries)
                time.sleep(wait)
                continue

            if resp.status_code == 429:
                last_error = RateLimitError("HTTP 429 Too Many Requests")
                self._pause_rate_limit(attempt)
                continue

            if resp.status_code >= 500:
                last_error = LeaguepediaError(f"HTTP {resp.status_code}")
                wait = min(30, 3 * attempt)
                logger.warning("服务器错误 %d，%d 秒后重试", resp.status_code, wait)
                time.sleep(wait)
                continue

            try:
                resp.raise_for_status()
                data = resp.json()
            except (requests.HTTPError, ValueError) as exc:
                last_error = exc
                time.sleep(min(30, 3 * attempt))
                continue

            if "error" in data:
                code = data["error"].get("code", "")
                info = data["error"].get("info", "unknown error")
                if code == "ratelimited":
                    last_error = RateLimitError(info)
                    self._pause_rate_limit(attempt)
                    continue
                raise LeaguepediaError(f"API 错误: {info}")

            return data

        if isinstance(last_error, RateLimitError):
            raise LeaguepediaError(
                f"多次限流后仍失败（已重试 {self.max_retries} 次），请稍后再运行爬虫"
            ) from last_error
        raise LeaguepediaError(f"请求失败（已重试 {self.max_retries} 次）: {last_error}") from last_error

    @staticmethod
    def parse_league(tournament: str) -> str:
        if not tournament:
            return "Unknown"
        for name in sorted(KNOWN_LEAGUES, key=len, reverse=True):
            if name.lower() in tournament.lower():
                return name
        match = re.match(r"^([A-Za-z][A-Za-z0-9 ]{1,20})", tournament)
        if match:
            return match.group(1).strip()[:64]
        return tournament[:64]

    @staticmethod
    def parse_datetime(value: str | None) -> datetime:
        if not value:
            raise ValueError("missing DateTime_UTC")
        value = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValueError(f"unsupported datetime: {value}")

    @staticmethod
    def parse_winner(team1: str, team2: str, winner_flag: str | None) -> str | None:
        if winner_flag == "1":
            return team1
        if winner_flag == "2":
            return team2
        return None

    @staticmethod
    def format_actual_result(
        team1: str,
        team2: str,
        score1: str | None,
        score2: str | None,
        winner: str | None,
    ) -> str:
        score_part = ""
        if score1 is not None and score2 is not None:
            score_part = f" ({score1}-{score2})"
        if winner:
            return f"{winner} 胜{score_part}"
        if score1 is not None and score2 is not None:
            return f"{team1} {score1}-{score2} {team2}"
        return f"{team1} vs {team2}"

    def row_to_match_kwargs(self, row: dict[str, Any]) -> dict[str, Any]:
        team1 = (row.get("Team1") or "").strip()
        team2 = (row.get("Team2") or "").strip()
        tournament = (row.get("Tournament") or "").strip()
        game_id = (row.get("GameId") or "").strip()
        dt_raw = row.get("DateTime UTC") or row.get("DateTime_UTC")

        if not team1 or not team2:
            raise ValueError("incomplete teams")
        if not game_id:
            raise ValueError("missing GameId")

        winner = self.parse_winner(team1, team2, row.get("Winner"))
        match_time = self.parse_datetime(dt_raw)

        return {
            "external_id": game_id,
            "league": self.parse_league(tournament),
            "blue_team": team1,
            "red_team": team2,
            "winner": winner,
            "match_time": match_time,
            "patch_version": (row.get("Patch") or "")[:32] or None,
            "actual_result": self.format_actual_result(
                team1,
                team2,
                row.get("Team1Score"),
                row.get("Team2Score"),
                winner,
            ),
        }
