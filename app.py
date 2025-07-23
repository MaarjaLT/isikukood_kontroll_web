from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, QueryLog
from datetime import datetime
import pandas as pd  # ← lisa see
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
    result = "Tundmatu viga"
    can_issue = False

    if not personal_id or len(personal_id) < 7:
        return jsonify({"result": "Vigane isikukood", "can_issue_ticket": False})

    # ✅ Kontrolli, kas juba on väljastatud
    log_path = "logi.xlsx"
    if os.path.exists(log_path):
        try:
            df_log = pd.read_excel(log_path)
            if not df_log.empty and personal_id in df_log[df_log["tulemus"] == "Tasuta pilet!"]["isikukood"].astype(str).values:
                return jsonify({"result": "Pilet juba väljastatud!", "can_issue_ticket": False})
        except Exception as e:
            return jsonify({"result": f"Logi lugemise viga: {str(e)}", "can_issue_ticket": False})

    # ✅ Kontroll nimekirjas
    try:
        andmed_df = pd.read_excel('andmed.xlsx')
        andmekoodid = andmed_df['isikukood'].astype(str).values
    except Exception as e:
        return jsonify({"result": f"Andmete faili lugemine ebaõnnestus: {str(e)}", "can_issue_ticket": False})

    if personal_id in andmekoodid:
        result = "Tasuta pilet!"
        can_issue = True

    else:
        # ✅ Arvuta vanus seisuga 01.08.2025
        try:
            yy = int(personal_id[1:3])
            mm = int(personal_id[3:5])
            dd = int(personal_id[5:7])
            century_code = personal_id[0]

            if century_code in ['1', '2']:
                year = 1800 + yy
            elif century_code in ['3', '4']:
                year = 1900 + yy
            elif century_code in ['5', '6']:
                year = 2000 + yy
            else:
                return jsonify({"result": "Tundmatu sajandikood", "can_issue_ticket": False})

            birth_date = datetime(year, mm, dd)
            ref_date = datetime(2025, 8, 1)
            age = (ref_date - birth_date).days // 365

            if age < 14:
                result = "Tasuta pilet!"
                can_issue = True
            else:
                result = "Ei ole elanik."
                can_issue = False
	
		if age >= 14 and personal_id not in andmekoodid:
    		result = "Pilet maksab"
   		 can_issue = False
   		 can_buy = True
return jsonify({
    "result": result,
    "can_issue_ticket": can_issue,
    "can_buy_ticket": can_buy
})


                # ✅ Salvesta puuduja
                try:
                    puuduja_path = "puuduja.xlsx"
                    puudu_row = {
                        "isikukood": personal_id,
                        "kasutaja": current_user.username,
                        "aeg": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        "põhjus": "≥14 ja puudub nimekirjast"
                    }
                    if os.path.exists(puuduja_path):
                        puudu_df = pd.read_excel(puuduja_path)
                        puudu_df = pd.concat([puudu_df, pd.DataFrame([puudu_row])], ignore_index=True)
                    else:
                        puudu_df = pd.DataFrame([puudu_row])
                    puudu_df.to_excel(puuduja_path, index=False)
                except Exception as e:
                    return jsonify({"result": f"Puuduja salvestamisel viga: {str(e)}", "can_issue_ticket": False})
        except Exception as e:
            return jsonify({"result": f"Vanuse arvutamine ebaõnnestus: {str(e)}", "can_issue_ticket": False})

    # ✅ Salvestame logi
    try:
        save_row = {
            "isikukood": personal_id,
            "kasutaja": current_user.username,
            "aeg": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "tulemus": result
        }
        if os.path.exists(log_path):
            df_log = pd.read_excel(log_path)
            df_log = pd.concat([df_log, pd.DataFrame([save_row])], ignore_index=True)
        else:
            df_log = pd.DataFrame([save_row])
        df_log.to_excel(log_path, index=False)
    except Exception as e:
        return jsonify({"result": f"Logi salvestamine ebaõnnestus: {str(e)}", "can_issue_ticket": False})

    # ✅ Andmebaasi logi
    db_log = QueryLog(personal_id=personal_id, result=result, user_id=current_user.id)
    db.session.add(db_log)
    db.session.commit()

    return jsonify({"result": result, "can_issue_ticket": can_issue})

# ✔️ Piletite ostmine
@app.route("/buy_ticket", methods=["POST"])
@login_required
def buy_ticket():
    try:
        isikukood = request.form.get("personal_id")
        kogus = int(request.form.get("quantity"))
        hind = 15 * kogus
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        ost_row = {
            "isikukood": isikukood,
            "kogus": kogus,
            "hind (€)": hind,
            "kasutaja": current_user.username,
            "aeg": timestamp
        }

        ostud_path = "ostud.xlsx"
        if os.path.exists(ostud_path):
            df = pd.read_excel(ostud_path)
            df = pd.concat([df, pd.DataFrame([ost_row])], ignore_index=True)
        else:
            df = pd.DataFrame([ost_row])
        df.to_excel(ostud_path, index=False)

        return jsonify({"result": f"{kogus} pilet(it) ostetud, hind kokku {hind}€"})
    except Exception as e:
        return jsonify({"result": f"Ostu salvestamine ebaõnnestus: {str(e)}"})


@app.route('/stats')
@login_required
def stats():
    try:
        df = pd.read_excel("logi.xlsx")
        count = df[df["tulemus"] == "Tasuta pilet!"].shape[0]
        return jsonify({"count": count})
    except:
        return jsonify({"count": 0})

@app.route("/debug-users")
def debug_users():
    users = User.query.all()
    return "<br>".join([f"{u.username} – {u.password}" for u in users])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

