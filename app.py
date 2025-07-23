from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'salajane_voti'

# ✔️ Ühendus PostgreSQL andmebaasiga Renderist
# Loeme keskkonnast ja asendame vajadusel URL-i alguse
database_url = os.getenv('DATABASE_URL')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ✔️ Mudelid
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False) 


class QueryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_id = db.Column(db.String(20), nullable=False)
    result = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        return render_template("login.html", error="Vale kasutajanimi või parool")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        return "Ligipääs keelatud", 403

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return render_template("create_user.html", error="Kasutajanimi on juba võetud.")

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template("create_user.html")


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        current_user.password = new_password
        db.session.commit()
        return redirect(url_for('index'))
    return render_template("change_password.html")

@app.route('/')
@login_required
def index():
    return render_template("index.html")

@app.route('/check', methods=['POST'])
@login_required
def check():
    personal_id = request.form.get("personal_id")

    # Lihtne kontroll
    if not personal_id or len(personal_id) < 7:
        result = "Vigane isikukood"
    elif personal_id.startswith("6") or personal_id.startswith("5"):
        result = "Tasuta pilet!"
    else:
        result = "Ei ole elanik."

    # Salvestame logi
    log = QueryLog(personal_id=personal_id, result=result, user_id=current_user.id)
    db.session.add(log)
    db.session.commit()

    return jsonify({"result": result})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
