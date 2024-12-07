from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import random

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

# Ruta za Quiz
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    # Inicijalizacija ili resetovanje sesije za novi kviz
    if 'quiz_questions' not in session or request.method == 'GET':
        # Fetch 10 questions at the start of the quiz
        response = requests.get('https://opentdb.com/api.php?amount=10&type=multiple')
        if response.status_code != 200:
            flash('Failed to fetch quiz questions. Please try again later.')
            return redirect(url_for('home'))

        data = response.json()
        if 'results' not in data or not data['results']:
            flash('No quiz questions available. Please try again later.')
            return redirect(url_for('home'))

        # Prepare the quiz questions
        quiz_questions = []
        for question_data in data['results']:
            # Mix the correct answer with incorrect ones
            options = question_data['incorrect_answers'] + [question_data['correct_answer']]
            random.shuffle(options)
            
            quiz_questions.append({
                'question': question_data['question'],
                'options': options,
                'correct_answer': question_data['correct_answer']
            })

        # Store quiz questions in session
        session['quiz_questions'] = quiz_questions
        session['current_question_index'] = 0
        session['correct_count'] = 0
        session['total_questions'] = 10

    # If quiz is completed, redirect to results
    if session['current_question_index'] >= session['total_questions']:
        return redirect(url_for('results'))

    # Get current question
    current_question = session['quiz_questions'][session['current_question_index']]

    # Handle answer submission
    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        
        # Check if answer is correct
        if selected_answer == current_question['correct_answer']:
            session['correct_count'] += 1

        # Move to next question
        session['current_question_index'] += 1
        session.modified = True

        # Redirect to next question or results
        if session['current_question_index'] >= session['total_questions']:
            return redirect(url_for('results'))
        
        return redirect(url_for('quiz'))

    # Render current question
    return render_template('quiz.html', 
                           question=current_question['question'], 
                           options=current_question['options'], 
                           current_question=session['current_question_index'] + 1,
                           total_questions=session['total_questions'])

@app.route('/results')
def results():
    # Get final results
    correct_count = session.get('correct_count', 0)
    total_questions = session.get('total_questions', 10)
    
    # Clear session data
    session.pop('quiz_questions', None)
    session.pop('current_question_index', None)
    session.pop('correct_count', None)
    session.pop('total_questions', None)

    return render_template('results.html', 
                           correct_count=correct_count, 
                           total_questions=total_questions)

if __name__ == "__main__":
    app.run(debug=True)