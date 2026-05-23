"""将Playwright抓取的数据写入SQLite"""

from __future__ import annotations

import logging

from app import create_app, db
from app.models import Game, Player, Series
from scraper.playwright_scraper import GameData, PlayerData, SeriesData
from scraper.cache import SeriesCache

logger = logging.getLogger(__name__)


def save_series_data(series_list: list[SeriesData], cache: SeriesCache) -> dict[str, int]:
    """
    保存系列赛数据到数据库

    Args:
        series_list: 系列赛数据列表
        cache: 系列赛缓存

    Returns:
        统计信息: series_inserted, series_skipped, games_inserted, players_inserted
    """
    logger.info(f"[步骤10] 开始保存数据到数据库，共 {len(series_list)} 个系列赛")
    app = create_app()
    stats = {
        "series_inserted": 0,
        "series_skipped": 0,
        "games_inserted": 0,
        "players_inserted": 0,
    }

    with app.app_context():
        for i, series_data in enumerate(series_list):
            try:
                logger.info(f"[步骤10.{i+1}] 正在保存系列赛 {i+1}/{len(series_list)}: {series_data.blue_team} vs {series_data.red_team}")

                # 检查是否已存在
                if cache.contains(series_data.external_id):
                    logger.info(f"[步骤10.{i+1}.1] 系列赛已存在，跳过: {series_data.external_id}")
                    stats["series_skipped"] += 1
                    continue

                # 创建系列赛
                series = Series(
                    tournament=series_data.tournament,
                    blue_team=series_data.blue_team,
                    red_team=series_data.red_team,
                    blue_score=series_data.blue_score,
                    red_score=series_data.red_score,
                    winner=series_data.winner,
                    external_id=series_data.external_id,
                )
                db.session.add(series)
                db.session.flush()  # 获取series.id

                stats["series_inserted"] += 1
                cache.add(series_data.external_id)
                logger.info(f"[步骤10.{i+1}.2] 系列赛保存成功，ID: {series.id}")

                # 创建游戏
                for j, game_data in enumerate(series_data.games):
                    logger.info(f"[步骤10.{i+1}.3.{j+1}] 正在保存 Game {game_data.game_number}...")
                    game = Game(
                        series_id=series.id,
                        game_number=game_data.game_number,
                        duration=game_data.duration,
                        winner=game_data.winner,
                        external_id=game_data.external_id,
                    )
                    db.session.add(game)
                    db.session.flush()  # 获取game.id

                    stats["games_inserted"] += 1
                    logger.info(f"[步骤10.{i+1}.3.{j+1}.1] Game {game_data.game_number} 保存成功，ID: {game.id}")

                    # 创建玩家
                    for k, player_data in enumerate(game_data.players):
                        player = Player(
                            game_id=game.id,
                            team=player_data.team,
                            player_name=player_data.player_name,
                            champion=player_data.champion,
                            summoner_spells=player_data.summoner_spells,
                            role=player_data.role,
                            kills=player_data.kills,
                            deaths=player_data.deaths,
                            assists=player_data.assists,
                            cs=player_data.cs,
                            gold=player_data.gold,
                            towers=player_data.towers,
                            items=player_data.items,
                        )
                        db.session.add(player)
                        stats["players_inserted"] += 1

                    logger.info(f"[步骤10.{i+1}.3.{j+1}.2] Game {game_data.game_number} 玩家数据保存完成，共 {len(game_data.players)} 个玩家")

                logger.info(f"[步骤10.{i+1}.4] 系列赛 {series_data.blue_team} vs {series_data.red_team} 全部数据保存完成")

            except Exception as e:
                logger.error(f"[步骤10.{i+1}失败] 保存系列赛失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        try:
            db.session.commit()
            logger.info(f"[步骤11] 数据库提交成功")
        except Exception as e:
            logger.error(f"[步骤11失败] 数据库提交失败: {e}")
            db.session.rollback()
            import traceback
            logger.error(traceback.format_exc())
            raise

    logger.info(f"[步骤12] 数据保存完成，统计: {stats}")
    return stats
