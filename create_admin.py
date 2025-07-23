import os
from dotenv import load_dotenv
from app import db, User, app
from werkzeug.security import generate_password_hash
from getpass import getpass

# ✅ Laeme keskkonnamuutujad
load_dotenv()
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

def create_admin():
    username = input("Sisesta admin kasutajanimi: ")
    password = getpass("Sisesta parool: ")

    with app.app_context():
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"⚠️ Kasutaja '{username}' on juba olemas.")
            return

        hashed_pw = generate_password_hash(password)
        admin = User(username=username, password=hashed_pw)
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Admin kasutaja '{username}' loodud.")

if __name__ == "__main__":
    create_admin()
