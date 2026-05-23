from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

from config import Config

db = SQLAlchemy()

SERIES_COLUMNS = {
    "id",
    "tournament",
    "blue_team",
    "red_team",
    "blue_score",
    "red_score",
    "winner",
    "external_id",
    "created_at",
}

GAME_COLUMNS = {
    "id",
    "series_id",
    "game_number",
    "duration",
    "winner",
    "external_id",
}

PLAYER_COLUMNS = {
    "id",
    "game_id",
    "team",
    "player_name",
    "champion",
    "summoner_spells",
    "role",
    "kills",
    "deaths",
    "assists",
    "cs",
    "gold",
    "towers",
    "items",
}


def _ensure_database():
    from app.models import Series, Game, Player

    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    # Check if tables exist and have correct schema
    for table_name, columns, model in [
        ("series", SERIES_COLUMNS, Series),
        ("games", GAME_COLUMNS, Game),
        ("players", PLAYER_COLUMNS, Player),
    ]:
        if table_name not in tables:
            db.create_all()
            return

        existing = {col["name"] for col in inspector.get_columns(table_name)}
        if existing != columns:
            model.__table__.drop(db.engine)
            db.create_all()
            return


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from app.routes import main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        _ensure_database()

    return app
