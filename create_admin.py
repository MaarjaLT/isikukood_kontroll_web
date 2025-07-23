from getpass import getpass
from werkzeug.security import generate_password_hash
from app import app
from models import db, User

def create_admin():
    username = input("Sisesta admin kasutajanimi: ")
    password = getpass("Sisesta parool: ")

    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"⚠️ Kasutaja '{username}' on juba olemas.")
            return

        hashed_pw = generate_password_hash(password)
        admin = User(username=username, password=hashed_pw, is_admin=True)
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Admin kasutaja '{username}' loodud.")

if __name__ == "__main__":
    create_admin()
