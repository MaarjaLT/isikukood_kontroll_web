from flask import Flask, render_template, request, jsonify
import pandas as pd
import datetime
import os

app = Flask(__name__)

# Exceli faili nimi (Renderis võib kaust olla teine, kasutame os.path)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, "andmed.xlsx")
HISTORY_FILE = os.path.join(BASE_DIR, "ajalugu.xlsx")

SHEET_NAME = "Sheet1"
ID_COLUMN = "Isikukood"
CHECKED_COLUMN = "Küsitud"
TICKET_COLUMN = "Pilet väljastatud"


def load_excel():
    """Laeb Exceli andmed, kui fail on olemas."""
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
    """Salvestab uuendatud Exceli andmed."""
    with pd.ExcelWriter(FILE_NAME, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)


def extract_birth_year(personal_id):
    """Leiab sünniaasta isikukoodist."""
    current_year = datetime.datetime.now().year
    century_map = {"1": 1800, "2": 1800, "3": 1900, "4": 1900, "5": 2000, "6": 2000}
    century = century_map.get(personal_id[0], 2000)
    birth_year = century + int(personal_id[1:3])
    return current_year - birth_year


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/check', methods=['POST'])
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
def issue_ticket():
    df = load_excel()
    personal_id = request.form.get("personal_id")
    df.loc[df[ID_COLUMN] == personal_id, TICKET_COLUMN] = "Jah"
    save_excel(df)
    return jsonify({"result": "Pilet väljastatud."})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
