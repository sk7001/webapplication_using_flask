from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
import mysql.connector
from mysql.connector import errorcode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# MySQL database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': '',  # Replace with your MySQL password
    'database': 'flaskpyweb'  # Replace with your desired MySQL database name
}

# Function to initialize the database and table
def init_db():
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        cursor = conn.cursor()

        # Create database if it does not exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(db_config['database']))
        conn.database = db_config['database']
        cursor.execute("USE {}".format(db_config['database']))

        # Create users table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        )
        """)

        conn.commit()  # Commit changes to the database

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        cursor.close()
        conn.close()

# Initialize the database and table
init_db()

# Connect to the database
db = mysql.connector.connect(**db_config)

# WTForms for user input validation
class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class SignInForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

# Routes
@app.route('/')
def index():
    return redirect(url_for('signin'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            db.commit()
            cursor.close()
            flash('Account created successfully! You can now sign in.', 'success')
            return redirect(url_for('signin'))
        except mysql.connector.Error as err:
            print(f"Error: {err}")  # Print the error to the console for debugging
            flash(f"Error: {err}", 'danger')
            db.rollback()
            cursor.close()
    return render_template('signup.html', form=form)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SignInForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            session['username'] = username
            flash(f"Welcome, {username}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('signin.html', form=form)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please sign in to access this page.', 'danger')
        return redirect(url_for('signin'))

    # Example products (replace with actual fetching from database)
    products = [
        {'name': 'Product 1', 'description': 'Description of Product 1', 'price': 19.99, 'image_url': 'https://via.placeholder.com/300'},
        {'name': 'Product 2', 'description': 'Description of Product 2', 'price': 29.99, 'image_url': 'https://via.placeholder.com/300'},
        {'name': 'Product 3', 'description': 'Description of Product 3', 'price': 39.99, 'image_url': 'https://via.placeholder.com/300'},
    ]

    return render_template('dashboard.html', username=session['username'], products=products)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)
