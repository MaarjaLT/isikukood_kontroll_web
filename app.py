from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from functools import wraps
import pandas as pd
import datetime
import os

app = Flask(__name__)
app.secret_key = 'väga_salajane_võti'

# Admin kasutaja (lihtsustatud)
USERNAME = "admin"
PASSWORD = "1234"

# Failide teed
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, "andmed.xlsx")
HISTORY_FILE = os.path.join(BASE_DIR, "ajalugu.xlsx")

# Exceli veerud
SHEET_NAME = "Sheet1"
ID_COLUMN = "Isikukood"
CHECKED_COLUMN = "Küsitud"
TICKET_COLUMN = "Pilet väljastatud"

# --- Autentimine ---
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template("login.html", error="Vale kasutajanimi või parool")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Exceli loogika ---
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

# --- Veebirouted ---
@app.route('/')
@login_required
def index():
    return render_template("index.html")

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
            return jsonify({"result": "Tasuta pilet!", "can_issue_ticket": True})
        return jsonify({"result": "Ei ole elanik.", "can_issue_ticket": False})
    
    if df.loc[df[ID_COLUMN] == personal_id, TICKET_COLUMN].values[0] == "Jah":
        return jsonify({"result": "Pilet juba väljastatud.", "can_issue_ticket": False})

    if age <= 14:
        return jsonify({"result": "Tasuta pilet!", "can_issue_ticket": True})

    df.loc[df[ID_COLUMN] == personal_id, CHECKED_COLUMN] = "Jah"
    save_excel(df)
    return jsonify({"result": "Elanik.", "can_issue_ticket": True})

@app.route('/issue_ticket', methods=['POST'])
@login_required
def issue_ticket():
    df = load_excel()
    personal_id = request.form.get("personal_id")
    df.loc[df[ID_COLUMN] == personal_id, TICKET_COLUMN] = "Jah"
    save_excel(df)
    return jsonify({"result": "Pilet väljastatud."})

# --- Käivita server Renderis ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
