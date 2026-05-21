from datetime import datetime

from app import db


class Match(db.Model):
    """比赛记录（示例模型，后续可扩展）"""

    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Match {self.title}>"
