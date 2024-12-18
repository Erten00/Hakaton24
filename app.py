from flask import Flask, render_template, jsonify, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import html
import random
from datetime import datetime  # Add this import

app = Flask(__name__)
app.secret_key = "tajna_kljucccc"  # Secret key for session management

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_app.db'  # SQLite database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Database models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    scores = db.relationship('Score', backref='user', lazy=True)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())

# def get_hint(question): 
#     # Make the API call
#     chat_completion = client.chat.completions.create(
#         messages=[
#             {"role": "user", "content": "Provide a hint for the question: " + question}
#         ],
#         model="gpt-4"  # Ensure to use the correct model name (e.g., gpt-4, not gpt-4o)
#     )
    
#     # Access the hint from the response using dot notation
#     hint = chat_completion.choices[0].message.content
    
#     return hint

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    categories = [
        {"id": 9, "name": "General Knowledge"},
        {"id": 10, "name": "Entertainment: Books"},
        {"id": 11, "name": "Entertainment: Film"},
        {"id": 12, "name": "Entertainment: Music"},
        {"id": 17, "name": "Science & Nature"},
        {"id": 18, "name": "Science: Computers"},
        {"id": 21, "name": "Sports"},
        {"id": 23, "name": "History"},
    ]

    if request.method == 'POST':
        selected_category = request.form.get('category')
        if selected_category:
            session['selected_category'] = selected_category
            return redirect(url_for('quiz'))
        else:
            flash('Please select a category before proceeding.')

    return render_template('index.html', categories=categories)

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect to home page or quiz if the user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))  # or 'quiz' depending on your preference

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')  # Add category
            return redirect(url_for('register'))

        # Add new user to database
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        try:
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}')
            return redirect(url_for('login'))

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect to home page or quiz if the user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))  # or 'quiz' depending on your preference

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Successfully logged in!', 'success')  # Add category
            return redirect(url_for('dashboard'))  # Correct redirect URL
        else:
            flash('Invalid username or password.', 'error')  # Add category

    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out!', 'success')  # Add category
    return redirect(url_for('home'))

@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    if 'api_token' not in session:
        token_response = requests.get('https://opentdb.com/api_token.php?command=request')
        if token_response.status_code == 200:
            session['api_token'] = token_response.json().get('token')
        else:
            flash('Failed to initialize quiz session. Try again later.', 'error')  # Add category
            return redirect(url_for('home'))

    if 'quiz_questions' not in session or not session.get('quiz_questions'):
        token = session['api_token']
        category = session.get('selected_category', 9)  # Default to General Knowledge
        quiz_response = requests.get(f'https://opentdb.com/api.php?amount=10&category={category}&type=multiple&token={token}')
        if quiz_response.status_code != 200 or not quiz_response.json().get('results'):
            flash('Failed to fetch quiz questions. Please try again later.', 'error')  # Add category
            return redirect(url_for('home'))

        quiz_data = quiz_response.json()
        session['quiz_questions'] = []
        for question in quiz_data['results']:
            options = question['incorrect_answers'] + [question['correct_answer']]
            random.shuffle(options)
            session['quiz_questions'].append({
                'question': question['question'],
                'options': options,
                'correct_answer': question['correct_answer'],
                'explanation': question.get('explanation', 'No explanation available.')
            })

        session['current_question_index'] = 0
        session['correct_count'] = 0
        session['total_questions'] = len(session['quiz_questions'])
        session.permanent = True

    current_index = session.get('current_question_index', 0)
    if current_index >= session['total_questions']:
        return redirect(url_for('dashboard'))

    current_question = session['quiz_questions'][current_index]
    decoded_question = html.unescape(current_question['question'])  # Decoding HTML entities

    feedback = None  # Initialize feedback as None

    if request.method == 'POST':
        selected_answer = request.form.get('answer')
        if not selected_answer:
            flash('Please select an answer before submitting.', 'error')  # Add category
            return redirect(url_for('quiz'))

        if selected_answer == current_question['correct_answer']:
            session['correct_count'] += 1

        session['current_question_index'] += 1
        session.modified = True

        if session['current_question_index'] >= session['total_questions']:
            return redirect(url_for('dashboard'))

        return redirect(url_for('quiz'))

    # Handle hint request
    # if request.args.get('hint'):
    #     hint = get_hint(decoded_question)
    #     return jsonify({'hint': hint})

    return render_template(
        'quiz.html',
        question=decoded_question,
        options=current_question['options'],
        current_question=current_index + 1,
        total_questions=session['total_questions'],
        feedback=feedback  # Pass feedback to the template
    )


# Results route
@app.route('/results', methods=['GET', 'POST'])
@login_required
def results():
    correct_count = session.get('correct_count', 0)
    total_questions = session.get('total_questions', 10)

    new_score = Score(user_id=current_user.id, score=correct_count, total_questions=total_questions)
    db.session.add(new_score)
    db.session.commit()

    session.pop('quiz_questions', None)
    session.pop('current_question_index', None)
    session.pop('correct_count', None)
    session.pop('total_questions', None)

    return render_template('results.html', correct_count=correct_count, total_questions=total_questions)

# Scores route
@app.route('/scores')
@login_required
def scores():
    user_scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.date.desc()).all()
    return render_template('scores.html', scores=user_scores)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # Handle quiz results if the user just finished a quiz
    correct_count = session.pop('correct_count', None)
    total_questions = session.pop('total_questions', None)

    if correct_count is not None and total_questions is not None:
        flash(f'Congratulations! You just finished your quiz. Score: {correct_count}/{total_questions}', 'success')

        # Save the user's latest score in the database
        try:
            new_score = Score(user_id=current_user.id, score=correct_count, total_questions=total_questions)
            db.session.add(new_score)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while saving your score: {e}", "error")

    # Clear any remaining quiz-related session data
    session.pop('quiz_questions', None)
    session.pop('current_question_index', None)

    # Prepare category and difficulty options for quiz selection
    categories = [
        {"id": 9, "name": "General Knowledge"},
        {"id": 10, "name": "Entertainment: Books"},
        {"id": 11, "name": "Entertainment: Film"},
        {"id": 12, "name": "Entertainment: Music"},
        {"id": 17, "name": "Science & Nature"},
        {"id": 18, "name": "Science: Computers"},
        {"id": 21, "name": "Sports"},
        {"id": 23, "name": "History"},
    ]
    difficulties = ["easy", "medium", "hard"]

    # Handle form submission for new quiz selection
    if request.method == 'POST':
        selected_category = request.form.get('category')
        selected_difficulty = request.form.get('difficulty')

        if selected_category and selected_difficulty:
            session['selected_category'] = selected_category
            session['selected_difficulty'] = selected_difficulty
            return redirect(url_for('quiz'))
        else:
            flash('Please select both a category and a difficulty.', 'error')

    # Fetch leaderboard (Top 10 scores)
    try:
        leaderboard = (
            db.session.query(User.username, Score.score, Score.total_questions, Score.date)
                .join(User, User.id == Score.user_id)
                .order_by(Score.score.desc(), Score.date.asc())
                .limit(10)
                .all()
    )
    except Exception as e:
        flash(f"An error occurred while fetching the leaderboard: {e}", "error")
        leaderboard = []

    # Fetch user's own scores
    try:
        user_scores = (
            Score.query.filter_by(user_id=current_user.id)
            .order_by(Score.date.desc())
            .all()
        )
    except Exception as e:
        flash(f"An error occurred while fetching your scores: {e}", "error")
        user_scores = []

    return render_template(
        'dashboard.html',
        categories=categories,
        difficulties=difficulties,
        leaderboard=leaderboard,
        user_scores=user_scores,
        enumerate=enumerate  # Pass enumerate if needed for template logic
    )

# Start route
@app.route('/start')
@login_required
def start():
    return render_template('start.html')  # This will render the start page.

@app.before_request
def before_request():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            login_user(user)

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensures database and tables are created

    app.run(debug=True)