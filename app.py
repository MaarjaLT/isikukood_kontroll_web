from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, QueryLog
from datetime import datetime
import os
from flask import flash

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'devkey')

# ✔️ Andmebaas
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ✔️ Login süsteem
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ✔️ Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        return render_template("login.html", error="Vale kasutajanimi või parool")
    return render_template("login.html")

# ✔️ Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ✔️ Admin kasutaja loomine
@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        return "Ligipääs keelatud", 403

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash("Paroolid ei kattu!", "danger")
            return render_template("create_user.html")

        if User.query.filter_by(username=username).first():
            flash("⚠️ Kasutajanimi on juba olemas!", "warning")
            return render_template("create_user.html")

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash(f"Kasutaja '{username}' loodud!", "success")
        return redirect(url_for('create_user'))

    return render_template("create_user.html")

# ✔️ Parooli muutmine
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template("change_password.html")

# ✔️ Avaleht
@app.route('/')
@login_required
def index():
    return render_template("index.html")

# ✔️ Isikukoodi kontroll
@app.route('/check', methods=['POST'])
@login_required
def check():
    personal_id = request.form.get("personal_id")
    if not personal_id or len(personal_id) < 7:
        result = "Vigane isikukood"
    elif personal_id.startswith("6") or personal_id.startswith("5"):
        result = "Tasuta pilet!"
    else:
        result = "Ei ole elanik."

    log = QueryLog(personal_id=personal_id, result=result, user_id=current_user.id)
    db.session.add(log)
    db.session.commit()

    return jsonify({"result": result})

@app.route("/debug-users")
def debug_users():
    users = User.query.all()
    return "<br>".join([f"{u.username} – {u.password}" for u in users])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

