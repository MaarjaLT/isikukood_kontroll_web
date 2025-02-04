import pandas as pd
import openpyxl
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import datetime

# Exceli faili nimi
FILE_NAME = "andmed.xlsx"
SHEET_NAME = "Sheet1"  # Muuda vastavalt vajadusele
ID_COLUMN = "Isikukood"  # Muuda vastavalt veeru nimele
CHECKED_COLUMN = "Küsitud"  # Veerg, kuhu märgitakse kontrollitud isikukoodid
TICKET_COLUMN = "Pilet väljastatud"  # Veerg piletiväljastuse märkimiseks
HISTORY_FILE = "ajalugu.xlsx"


def load_excel(file_name):
    """Laeb Exceli andmed DataFrame'ina ja lisab vajalikud veerud, kui neid pole."""
    try:
        df = pd.read_excel(file_name, sheet_name=SHEET_NAME, dtype=str)
        df.columns = df.columns.str.strip()
        if CHECKED_COLUMN not in df.columns:
            df[CHECKED_COLUMN] = "Ei"
        if TICKET_COLUMN not in df.columns:
            df[TICKET_COLUMN] = "Ei"
        return df
    except FileNotFoundError:
        messagebox.showerror("Viga", f"Faili '{file_name}' ei leitud.")
        return None


def save_excel(df, file_name):
    """Salvestab uuendatud DataFrame'i Exceli faili."""
    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)


def save_to_history(personal_id):
    """Lisab isikukoodi ajaloo Excelisse."""
    try:
        history_df = pd.read_excel(HISTORY_FILE, dtype=str)
    except FileNotFoundError:
        history_df = pd.DataFrame(columns=[ID_COLUMN])
    
    if personal_id not in history_df[ID_COLUMN].values:
        new_row = pd.DataFrame([{ID_COLUMN: personal_id}])
        history_df = pd.concat([history_df, new_row], ignore_index=True)
        with pd.ExcelWriter(HISTORY_FILE, engine='openpyxl') as writer:
            history_df.to_excel(writer, index=False)


def extract_birth_year(personal_id):
    """Leiab isikukoodist sünniaasta."""
    current_year = datetime.datetime.now().year
    century_map = {"1": 1800, "2": 1800, "3": 1900, "4": 1900, "5": 2000, "6": 2000}
    century = century_map.get(personal_id[0], 2000)
    birth_year = century + int(personal_id[1:3])
    age = current_year - birth_year
    return age


def check_personal_id(df, personal_id):
    """Kontrollib isikukoodi ning märgib tasuta pileti alla 14-aastastele."""
    age = extract_birth_year(personal_id)
    if personal_id in df[ID_COLUMN].values:
        if df.loc[df[ID_COLUMN] == personal_id, TICKET_COLUMN].values[0] == "Jah":
            messagebox.showinfo("Tulemus", "Pilet juba väljastatud.")
            return df, True
        elif age <= 14:
            messagebox.showinfo("Tulemus", "Tasuta pilet!")
            df.loc[df[ID_COLUMN] == personal_id, TICKET_COLUMN] = "Jah"
            return df, True
        else:
            df.loc[df[ID_COLUMN] == personal_id, CHECKED_COLUMN] = "Jah"
            messagebox.showinfo("Tulemus", "Elanik.")
    else:
        save_to_history(personal_id)
        if age <= 14:
            messagebox.showinfo("Tulemus", "Tasuta pilet!")
            new_row = pd.DataFrame([{ID_COLUMN: personal_id, CHECKED_COLUMN: "Jah", TICKET_COLUMN: "Jah"}])
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            messagebox.showinfo("Tulemus", "Ei ole elanik.")
    return df, False


def on_check():
    df = load_excel(FILE_NAME)
    if df is None:
        return

    personal_id = id_entry.get()
    if personal_id:
        df_updated, ticket_already_issued = check_personal_id(df, personal_id)
        save_excel(df_updated, FILE_NAME)
        ticket_checkbox.config(state=tk.DISABLED if ticket_already_issued else tk.NORMAL)


def reset_form():
    """Lähtestab vormi uueks päringuks."""
    id_entry.delete(0, tk.END)
    ticket_checkbox.config(state=tk.NORMAL)
    ticket_var.set(False)


def check_id_ui():
    """Kasutajaliides isikukoodi kontrollimiseks."""
    global id_entry, ticket_var, ticket_checkbox

    root = tk.Tk()
    root.title("Isikukoodi kontroll")
    
    tk.Label(root, text="Sisesta isikukood:").grid(row=0, column=0)
    id_entry = tk.Entry(root)
    id_entry.grid(row=0, column=1)
    
    check_button = tk.Button(root, text="Kontrolli", command=on_check)
    check_button.grid(row=1, columnspan=2)
    
    ticket_var = tk.BooleanVar()
    ticket_checkbox = ttk.Checkbutton(root, text="Pilet väljastatud", variable=ticket_var)
    ticket_checkbox.grid(row=2, columnspan=2)
    
    reset_button = tk.Button(root, text="Uus päring", command=reset_form)
    reset_button.grid(row=3, columnspan=2)
    
    root.mainloop()


if __name__ == "__main__":
    check_id_ui()
