from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Andmebaasi initsialiseerimine
db = SQLAlchemy()

# Kasutajate tabel
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

# Päringute logi
class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_id = db.Column(db.String(20), nullable=False)
    result = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
