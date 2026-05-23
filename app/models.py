from app import db


class Series(db.Model):
    """系列赛（BO3/BO5）"""

    __tablename__ = "series"

    id = db.Column(db.Integer, primary_key=True)
    tournament = db.Column(db.String(128), nullable=False, comment="赛事名称")
    blue_team = db.Column(db.String(128), nullable=False, comment="蓝方队伍")
    red_team = db.Column(db.String(128), nullable=False, comment="红方队伍")
    blue_score = db.Column(db.Integer, default=0, nullable=False, comment="蓝方得分")
    red_score = db.Column(db.Integer, default=0, nullable=False, comment="红方得分")
    winner = db.Column(db.String(128), nullable=True, comment="胜者")
    external_id = db.Column(db.String(256), unique=True, nullable=True, comment="外部数据源ID")
    created_at = db.Column(db.DateTime, server_default=db.func.now(), comment="创建时间")

    games = db.relationship("Game", backref="series", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Series {self.blue_team} vs {self.red_team} ({self.blue_score}-{self.red_score})>"


class Game(db.Model):
    """单局比赛"""

    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"), nullable=False)
    game_number = db.Column(db.Integer, nullable=False, comment="第几局")
    duration = db.Column(db.String(32), nullable=True, comment="比赛时长")
    winner = db.Column(db.String(128), nullable=True, comment="胜者")
    external_id = db.Column(db.String(256), unique=True, nullable=True, comment="外部数据源ID")

    players = db.relationship("Player", backref="game", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Game {self.series.blue_team} vs {self.series.red_team} - Game {self.game_number}>"


class Player(db.Model):
    """玩家数据"""

    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    team = db.Column(db.String(32), nullable=False, comment="队伍（blue/red）")
    player_name = db.Column(db.String(128), nullable=False, comment="选手名称")
    champion = db.Column(db.String(128), nullable=True, comment="英雄")
    summoner_spells = db.Column(db.String(64), nullable=True, comment="召唤师技能")
    role = db.Column(db.String(32), nullable=True, comment="位置")
    kills = db.Column(db.Integer, nullable=True, comment="击杀")
    deaths = db.Column(db.Integer, nullable=True, comment="死亡")
    assists = db.Column(db.Integer, nullable=True, comment="助攻")
    cs = db.Column(db.Integer, nullable=True, comment="补刀")
    gold = db.Column(db.Integer, nullable=True, comment="金币")
    towers = db.Column(db.Integer, nullable=True, comment="推塔")
    items = db.Column(db.Text, nullable=True, comment="装备")

    def __repr__(self):
        return f"<Player {self.player_name} ({self.champion})>"
