from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = "tajna_kljucccc"  # Neophodno za rad sesija

# Konfigurišemo Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Stranica za preusmeravanje ako korisnik nije prijavljen

# Kreiranje "baze podataka" korisnika (u memoriji za primer)
users = {"erten": {"password": "lozinka"}}

# Kreiramo User model koji Flask-Login koristi
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Loader funkcija za pronalaženje korisnika
@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

# Ruta za početnu stranicu
@app.route("/")
def home():
    return render_template("index.html", user=current_user)

# Ruta za login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username]["password"] == password:
            user = User(username)
            login_user(user)
            flash("Uspešno ste prijavljeni!")
            return redirect(url_for("home"))
        else:
            flash("Neispravno korisničko ime ili lozinka.")
    return render_template("login.html")

# Ruta za logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Uspešno ste odjavljeni!")
    return redirect(url_for("home"))

# Ruta za zaštićenu stranicu
@app.route("/protected")
@login_required
def protected():
    return f"Ovo je zaštićena stranica, {current_user.id}!"

if __name__ == "__main__":
    app.run(debug=True)
