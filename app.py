from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import pandas as pd
import datetime
import os

app = Flask(__name__)
app.secret_key = 'väga_salajane_võti'

# PostgreSQL ühendus (Renderi jaoks)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Algatame andmebaasi
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Mudelid
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_id = db.Column(db.String(20), nullable=False)
    result = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Exceli failid
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, "andmed.xlsx")
SHEET_NAME = "Sheet1"
ID_COLUMN = "Isikukood"
CHECKED_COLUMN = "Küsitud"
TICKET_COLUMN = "Pilet väljastatud"

def load_excel():
    try:
        df = pd.read_excel(FILE_NAME, sheet_name=SHEET_NAME, dtype=str)
        df.columns = df.columns.str.strip()
        if CHECKED_COLUMN not in df.columns:
            df[CHECKED_COLUMN] = "Ei"
        if TICKET_COLUMN not in df.columns:
            df[TICKET_COLUMN] = "Ei"
        return df
    except FileNotFoundError:
        return None

def save_excel(df):
    with pd.ExcelWriter(FILE_NAME, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

def extract_birth_year(personal_id):
    current_year = datetime.datetime.now().year
    century_map = {"1": 1800, "2": 1800, "3": 1900, "4": 1900, "5": 2000, "6": 2000}
    century = century_map.get(personal_id[0], 2000)
    birth_year = century + int(personal_id[1:3])
    return current_year - birth_year

@app.route('/')
@login_required
def index():
    return render_template("index.html")

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

@app.route('/check', methods=['POST'])
@login_required
def check_personal_id():
    df = load_excel()
    if df is None:
        return jsonify({"error": "Exceli faili ei leitud."})

    personal_id = request.form.get("personal_id")
    age = extract_birth_year(personal_id)

    if personal_id not in df[ID_COLUMN].values:
        if age <= 14:
            db.session.add(Query(personal_id=personal_id, result="Tasuta pilet!", user_id=current_user.id))
            db.session.commit()
            return jsonify({"result": "Tasuta pilet!", "can_issue_ticket": True})
        db.session.add(Query(personal_id=personal_id, result="Ei ole elanik.", user_id=current_user.id))
        db.session.commit()
        return jsonify({"result": "Ei ole elanik.", "can_issue_ticket": False})

    if df.loc[df[ID_COLUMN] == personal_id, TICKET_COLUMN].values[0] == "Jah":
        db.session.add(Query(personal_id=personal_id, result="Pilet juba väljastatud.", user_id=current_user.id))
        db.session.commit()
        return jsonify({"result": "Pilet juba väljastatud.", "can_issue_ticket": False})

    if age <= 14:
        db.session.add(Query(personal_id=personal_id, result="Tasuta pilet!", user_id=current_user.id))
        db.session.commit()
        return jsonify({"result": "Tasuta pilet!", "can_issue_ticket": True})

    df.loc[df[ID_COLUMN] == personal_id, CHECKED_COLUMN] = "Jah"
    save_excel(df)
    db.session.add(Query(personal_id=personal_id, result="Elanik.", user_id=current_user.id))
    db.session.commit()
    return jsonify({"result": "Elanik.", "can_issue_ticket": True})

@app.route('/issue_ticket', methods=['POST'])
@login_required
def issue_ticket():
    df = load_excel()
    personal_id = request.form.get("personal_id")
    df.loc[df[ID_COLUMN] == personal_id, TICKET_COLUMN] = "Jah"
    save_excel(df)
    db.session.add(Query(personal_id=personal_id, result="Pilet väljastatud.", user_id=current_user.id))
    db.session.commit()
    return jsonify({"result": "Pilet väljastatud."})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)