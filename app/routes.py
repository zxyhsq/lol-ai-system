from flask import Blueprint, abort, jsonify, render_template, request

from app import db
from app.models import Game, Player, Series
from scraper.cache import SeriesCache
from scraper.playwright_scraper import scrape_url
from scraper.playwright_store import save_series_data

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    series_list = Series.query.order_by(Series.created_at.desc()).all()
    return render_template("index.html", series=series_list)


@main_bp.route("/scrape", methods=["POST"])
def scrape():
    """抓取比赛数据"""
    url = request.json.get("url") if request.is_json else None
    if not url:
        url = "https://lol.fandom.com/wiki/CBLOL/2026_Season/Split_1_Playoffs/Scoreboards"

    try:
        # 抓取数据
        import asyncio

        series_list = asyncio.run(scrape_url(url, headless=True))

        # 保存到数据库
        cache = SeriesCache()
        cache.load_from_db()
        stats = save_series_data(series_list, cache)

        return jsonify({
            "success": True,
            "stats": stats,
            "message": f"成功抓取 {len(series_list)} 个系列赛"
        })
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@main_bp.route("/series/<int:series_id>")
def series_detail(series_id):
    series = db.session.get(Series, series_id)
    if series is None:
        abort(404)
    return render_template("series_detail.html", series=series)


@main_bp.route("/database")
def database_view():
    """数据库查看页面"""
    series_count = Series.query.count()
    game_count = Game.query.count()
    player_count = Player.query.count()

    series_list = Series.query.order_by(Series.created_at.desc()).limit(50).all()

    return render_template("database.html", 
                          series_count=series_count,
                          game_count=game_count,
                          player_count=player_count,
                          series_list=series_list)


@main_bp.route("/raw-data")
def raw_data_view():
    """原始数据查看页面"""
    series_list = Series.query.order_by(Series.created_at.desc()).limit(10).all()
    
    # 转换为JSON格式
    raw_data = []
    for series in series_list:
        series_dict = {
            "id": series.id,
            "tournament": series.tournament,
            "blue_team": series.blue_team,
            "red_team": series.red_team,
            "blue_score": series.blue_score,
            "red_score": series.red_score,
            "winner": series.winner,
            "external_id": series.external_id,
            "created_at": series.created_at.isoformat() if series.created_at else None,
            "games": []
        }
        
        for game in series.games:
            game_dict = {
                "id": game.id,
                "game_number": game.game_number,
                "duration": game.duration,
                "winner": game.winner,
                "external_id": game.external_id,
                "players": []
            }
            
            for player in game.players:
                player_dict = {
                    "id": player.id,
                    "team": player.team,
                    "player_name": player.player_name,
                    "champion": player.champion,
                    "summoner_spells": player.summoner_spells,
                    "role": player.role,
                    "kills": player.kills,
                    "deaths": player.deaths,
                    "assists": player.assists,
                    "cs": player.cs,
                    "gold": player.gold,
                    "towers": player.towers,
                    "items": player.items
                }
                game_dict["players"].append(player_dict)
            
            series_dict["games"].append(game_dict)
        
        raw_data.append(series_dict)
    
    return render_template("raw_data.html", raw_data=raw_data)
