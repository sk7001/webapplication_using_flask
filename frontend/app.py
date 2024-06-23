from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, URL
import mysql.connector
from config import ADMIN_USERNAME, ADMIN_PASSWORD

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# MySQL database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': '',  # Replace with your MySQL password
    'database': 'flaskpyweb'  # Replace with your desired MySQL database name
}

# Function to initialize the database and tables
def init_db():
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
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
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        )
        """)

        # Create products table if not exists
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2),
            image_url VARCHAR(255)
        )
        """)

        conn.commit()  # Commit changes to the database

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        cursor.close()
        conn.close()

# Initialize the database and tables
init_db()

# Connect to the database using Flask's context-sensitive g object
def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**db_config)
    return g.db

@app.teardown_appcontext
def teardown_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# WTForms for user input validation
class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Length(min=4, max=100)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class SignInForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(min=4, max=100)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    price = DecimalField('Price', validators=[DataRequired()])
    image_url = StringField('Image URL', validators=[DataRequired(), URL()])
    submit = SubmitField('Save Product')

# Routes
@app.route('/')
def index():
    return redirect(url_for('signin'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        cursor = get_db().cursor()
        try:
            # Check if the username or email already exists
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Username or email already exists. Please choose another.', 'danger')
            else:
                if email == "admin" and password == "admin":
                    flash('Account cannot be created with these credentials. Please choose another email and password.', 'danger')
                else:
                    cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
                    get_db().commit()
                    flash('Account created successfully! You can now sign in.', 'success')
                    return redirect(url_for('signin'))
        except mysql.connector.Error as err:
            print(f"Error: {err}")  # Print the error to the console for debugging
            flash(f"Error: {err}", 'danger')
            get_db().rollback()
        finally:
            cursor.close()
    return render_template('signup.html', form=form)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SignInForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = get_db().cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()
            cursor.close()

            if email == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['username'] = ADMIN_USERNAME  # Store admin username in session
                flash('Admin login successful.', 'success')
                return redirect(url_for('admindashboard'))
            elif user:
                session['username'] = user[1]  # Store regular user username in session
                flash(f"Welcome, {user[1]}!", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password', 'danger')
        except mysql.connector.Error as err:
            print(f"Error: {err}")  # Print the error to the console for debugging
            flash(f"Error: {err}", 'danger')

    return render_template('signin.html', form=form)




@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please sign in to access this page.', 'danger')
        return redirect(url_for('signin'))

    try:
        cursor = get_db().cursor()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()

        # If products is not empty, construct a list of dictionaries for easier access in Jinja template
        products_list = []
        for product in products:
            product_dict = {
                'id': product[0],
                'name': product[1],
                'description': product[2],
                'price': float(product[3]),  # Convert Decimal to float if needed
                'image_url': product[4]
            }
            products_list.append(product_dict)

        return render_template('dashboard.html', username=session['username'], products=products_list)

    except mysql.connector.Error as err:
        flash(f"Error retrieving products: {err}", 'danger')
        return redirect(url_for('signin'))

@app.route('/admindashboard', methods=['GET', 'POST'])
def admindashboard():
    if 'username' not in session:
        flash('Please sign in to access this page.', 'danger')
        return redirect(url_for('signin'))

    form = ProductForm()
    if form.validate_on_submit():
        name = form.name.data
        description = form.description.data
        price = form.price.data
        image_url = form.image_url.data

        cursor = get_db().cursor()
        try:
            cursor.execute("INSERT INTO products (name, description, price, image_url) VALUES (%s, %s, %s, %s)", (name, description, price, image_url))
            get_db().commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admindashboard'))
        except mysql.connector.Error as err:
            print(f"Error: {err}")  # Print the error to the console for debugging
            flash(f"Error: {err}", 'danger')
            get_db().rollback()
        finally:
            cursor.close()

    try:
        cursor = get_db().cursor()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()

        products_list = []
        for product in products:
            product_dict = {
                'id': product[0],
                'name': product[1],
                'description': product[2],
                'price': float(product[3]),  # Convert Decimal to float if needed
                'image_url': product[4]
            }
            products_list.append(product_dict)

        return render_template('admindashboard.html', username=session['username'], form=form, products=products_list)

    except mysql.connector.Error as err:
        flash(f"Error retrieving products: {err}", 'danger')
        return redirect(url_for('signin'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)
