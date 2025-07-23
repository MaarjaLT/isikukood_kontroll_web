from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, QueryLog
from datetime import datetime
import pandas as pd  # ← lisa see
from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from openpyxl import load_workbook

import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'devkey')

# Laeme Exceli tabeli siia
df = pd.read_excel("andmed.xlsx")  # ← lisa siia

# Andmebaas jne...

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
    return render_template("admin.html")

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
    timestamp = datetime.utcnow()

    if not personal_id or len(personal_id) < 7:
        return jsonify({"result": "Vigane isikukood", "can_issue_ticket": False, "can_sell_ticket": False})

    # Kontrolli kas on juba tasuta pilet saanud
    free_path = 'andmed.xlsx'
    already_free = False
    if os.path.exists(free_path):
        df_free = pd.read_excel(free_path)
        already_free = personal_id in df_free['isikukood'].astype(str).values

    if already_free:
        return jsonify({
            "result": "Tasuta pilet on juba väljastatud!",
            "can_issue_ticket": False,
            "can_sell_ticket": True  # ✅ saab osta lisaks!
        })

    # Kontrollime nimekirjast
    try:
        df = pd.read_excel(free_path)
        is_in_list = personal_id in df['isikukood'].astype(str).values
    except Exception:
        is_in_list = False

    if is_in_list:
        result = "Tasuta pilet!"
        can_issue = True
        can_sell = False
    else:
        try:
            century = {"1": "18", "2": "18", "3": "19", "4": "19", "5": "20", "6": "20"}[personal_id[0]]
            birth_year = int(century + personal_id[1:3])
            birth_month = int(personal_id[3:5])
            birth_day = int(personal_id[5:7])
            birthdate = datetime(birth_year, birth_month, birth_day)
            age = (datetime(2025, 8, 1) - birthdate).days // 365
        except:
            return jsonify({"result": "Sünnikuupäev vigane", "can_issue_ticket": False, "can_sell_ticket": False})

        if age < 14:
            result = "Tasuta pilet!"
            can_issue = True
            can_sell = False
        else:
            result = "Pileti müük"
            can_issue = False
            can_sell = True

    return jsonify({
        "result": result,
        "can_issue_ticket": can_issue,
        "can_sell_ticket": can_sell
    })

# ✔️ Pileti väljastamine
@app.route('/issue_ticket', methods=['POST'])
@login_required
def issue_ticket():
    personal_id = request.form.get("personal_id")
    timestamp = datetime.utcnow()
    row = {
        "isikukood": personal_id,
        "kasutaja": current_user.username,
        "aeg": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        "tulemus": "Tasuta pilet"
    }
    path = 'andmed.xlsx'
    try:
        if os.path.exists(path):
            df = pd.read_excel(path)
            if personal_id in df['isikukood'].astype(str).values:
                return jsonify({"result": "See isikukood on juba saanud tasuta pileti!"})
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            df = pd.DataFrame([row])
        df.to_excel(path, index=False)
    except Exception as e:
        return jsonify({"result": f"Salvestamine ebaõnnestus: {str(e)}"})
    return jsonify({"result": "Pilet väljastatud!"})

# ✔️ Pileti müümine
@app.route('/sell_ticket', methods=['POST'])
@login_required
def sell_ticket():
    personal_id = request.form.get("personal_id")
    quantity = int(request.form.get("quantity", 1))
    timestamp = datetime.utcnow()
    total_price = quantity * 15

    row = {
        "isikukood": personal_id,
        "kogus": quantity,
        "hind (€)": total_price,
        "kasutaja": current_user.username,
        "aeg": timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }

    path = 'müük.xlsx'
    try:
        if os.path.exists(path):
            df = pd.read_excel(path)
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            df = pd.DataFrame([row])
        df.to_excel(path, index=False)
    except Exception as e:
        return jsonify({"result": f"Müügi salvestus ebaõnnestus: {str(e)}"})

    return jsonify({"result": f"{quantity} pilet(it) müüdud, kokku {total_price} €"})

# ✔️ Debugimine
@app.route("/debug-users")
def debug_users():
    users = User.query.all()
    return "<br>".join([f"{u.username} – {u.password}" for u in users])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

