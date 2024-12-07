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


@app.before_request
def log_session_data():
    print(f"Session data: {dict(session)}")


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    # Ensure a valid session token exists
    if 'api_token' not in session:
        token_response = requests.get('https://opentdb.com/api_token.php?command=request')
        if token_response.status_code == 200:
            session['api_token'] = token_response.json().get('token')
        else:
            flash('Failed to initialize quiz session. Try again later.')
            return redirect(url_for('home'))

    # Initialize quiz questions if not already present
    if 'quiz_questions' not in session or not session.get('quiz_questions'):
        token = session['api_token']
        quiz_response = requests.get(f'https://opentdb.com/api.php?amount=10&type=multiple&token={token}')
        if quiz_response.status_code != 200 or not quiz_response.json().get('results'):
            flash('Failed to fetch quiz questions. Please try again later.')
            return redirect(url_for('home'))

        quiz_data = quiz_response.json()

        # Handle token exhaustion (response_code == 4)
        if quiz_data.get('response_code') == 4:
            reset_response = requests.get(f'https://opentdb.com/api_token.php?command=reset&token={token}')
            if reset_response.status_code == 200:
                flash('Question pool exhausted. Resetting quiz session.')
                return redirect(url_for('quiz'))
            else:
                flash('Failed to reset quiz session. Try again later.')
                return redirect(url_for('home'))

        # Prepare questions
        session['quiz_questions'] = []
        for question in quiz_data['results']:
            options = question['incorrect_answers'] + [question['correct_answer']]
            random.shuffle(options)
            session['quiz_questions'].append({
                'question': question['question'],
                'options': options,
                'correct_answer': question['correct_answer']
            })

        session['current_question_index'] = 0
        session['correct_count'] = 0
        session['total_questions'] = len(session['quiz_questions'])
        session.permanent = True

    # Retrieve current question
    current_index = session.get('current_question_index', 0)
    if current_index >= session['total_questions']:
        return redirect(url_for('results'))

    current_question = session['quiz_questions'][current_index]

    if request.method == 'POST':
        # Validate submitted answer
        selected_answer = request.form.get('answer')
        if not selected_answer:
            flash('Please select an answer before submitting.')
            return redirect(url_for('quiz'))

        # Check if the answer is correct
        if selected_answer == current_question['correct_answer']:
            session['correct_count'] += 1

        # Move to next question
        session['current_question_index'] += 1
        session.modified = True

        # Redirect to results if quiz is completed
        if session['current_question_index'] >= session['total_questions']:
            return redirect(url_for('results'))
        return redirect(url_for('quiz'))

    # Render quiz template
    return render_template(
        'quiz.html',
        question=current_question['question'],
        options=current_question['options'],
        current_question=current_index + 1,
        total_questions=session['total_questions']
    )



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
