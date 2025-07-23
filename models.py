from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Andmebaasi ühendus
db = SQLAlchemy()

# Kasutajate mudel
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Päringute logi
class QueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_id = db.Column(db.String(20), nullable=False)
    result = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
