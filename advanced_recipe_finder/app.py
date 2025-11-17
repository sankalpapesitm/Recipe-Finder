# -*- coding: utf-8 -*-
import os
import json
import mysql.connector
from mysql.connector import pooling
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import google.generativeai as genai
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import re
import requests
from uuid import uuid4
import logging
import urllib.parse
import pyotp
import qrcode
from io import BytesIO
import base64
import time
import threading
import random
import tempfile
import shutil
from fpdf import FPDF 
from functools import wraps
from bytez_image_generator import BytezImageGenerator
from config_backup import Config as AppConfig

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Store the originally requested URL
            session['next'] = request.url
            flash('Please log in to access this feature.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Configuration Class (inherits from config.py which has all API keys)
class Config(AppConfig):
    # Override database configuration if needed
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'recipefinder101'
    
    # Override upload folder
    UPLOAD_FOLDER = 'upload'
    
    # Gemini API Configuration (Text generation only)
    GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com'
    GEMINI_VERSION = 'v1'
    GEMINI_TEXT_MODEL = 'models/gemini-flash-latest'



# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Bytez Image Generator
bytez_generator = BytezImageGenerator(api_key=Config.BYTEZ_API_KEY)

# Cache for Gemini API responses
api_cache = {}
cache_lock = threading.Lock()
CACHE_TTL = 3600  # 1 hour

# Cache for database queries
db_cache = {}
db_cache_lock = threading.Lock()
DB_CACHE_TTL = 60  # 1 minute

def get_from_cache(key):
    with db_cache_lock:
        if key in db_cache:
            cached_data = db_cache[key]
            if time.time() - cached_data['timestamp'] < DB_CACHE_TTL:
                app.logger.info(f"Returning cached database response for key: {key}")
                return cached_data['data']
    return None

def set_to_cache(key, data):
    with db_cache_lock:
        db_cache[key] = {'data': data, 'timestamp': time.time()}

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set absolute path for upload folder and create it if it doesn't exist
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'upload')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Custom Jinja2 filter for splitting strings
@app.template_filter('split')
def split_filter(s, delimiter=','):
    """A custom Jinja2 filter to split a string."""
    if s is None:
        return []
    return s.split(delimiter)

# Custom Jinja2 filter for parsing JSON strings
@app.template_filter('fromjson')
def fromjson_filter(s):
    """A custom Jinja2 filter to parse JSON strings."""
    import json
    if s is None:
        return None
    return json.loads(s)

# Custom Jinja2 filter for converting newlines to HTML breaks
@app.template_filter('nl2br')
def nl2br_filter(s):
    """A custom Jinja2 filter to convert newlines to <br> tags."""
    if s is None:
        return None
    return s.replace('\n', '<br>')

# Custom Jinja2 filter for formatting analysis text
@app.template_filter('format_analysis')
def format_analysis_filter(s):
    """A custom Jinja2 filter to format analysis text with bold and proper spacing."""
    import re
    if s is None:
        return None
    # Replace escaped newlines with <br>
    s = s.replace('\\n', '<br>')
    # Replace **text** with <strong>text</strong>
    s = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', s)
    # Replace *text* with <strong>text</strong>
    s = re.sub(r'\*(.*?)\*', r'<strong>\1</strong>', s)
    # Remove any remaining standalone *
    s = s.replace('*', '')
    # Wrap in sections and handle double line breaks
    s = '<div class="analysis-section">' + s + '</div>'
    s = s.replace('<br><br>', '</div><div class="analysis-section">')
    return s

# Configure Gemini AI
genai.configure(api_key=app.config['GEMINI_API_KEY'])

# Database connection pooling
db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="recipe_pool",
    pool_size=10,
    pool_reset_session=True,
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)

def get_db_connection():
    try:
        connection = db_pool.get_connection()
        return connection
    except Error as e:
        app.logger.error(f"Error connecting to MySQL: {e}")
        return None
# Initialize database tables
def create_default_admin():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE is_admin = TRUE LIMIT 1')
        admin_exists = cursor.fetchone()
        if not admin_exists:
            hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
            cursor.execute('INSERT INTO users (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s)',
                           ('admin', 'admin@example.com', hashed_password, True))
            connection.commit()
        cursor.close()
        connection.close()

def init_db():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(200) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                dietary_preferences TEXT,
                allergies TEXT,
                image_url VARCHAR(255),
                otp_secret VARCHAR(16),
                is_2fa_enabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create recipes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                ingredients TEXT NOT NULL,
                instructions TEXT NOT NULL,
                cooking_time INT,
                difficulty ENUM('Easy', 'Medium', 'Hard'),
                category VARCHAR(100),
                image_url VARCHAR(300),
                image_prompt TEXT,
                nutritional_info TEXT,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        # Check if image_prompt column exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'recipes'
            AND column_name = 'image_prompt'
        """, (app.config['MYSQL_DB'],))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE recipes ADD COLUMN image_prompt TEXT")
        
        # Check if audio_url column exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'recipes'
            AND column_name = 'audio_url'
        """, (app.config['MYSQL_DB'],))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE recipes ADD COLUMN audio_url VARCHAR(300)")
        
        # Create favorites table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                recipe_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                UNIQUE(user_id, recipe_id)
            )
        ''')
        
        # Create meal_plans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meal_plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                plan_data TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Create chat_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        
        # Create generated_recipes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_recipes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                prompt TEXT NOT NULL,
                recipe_data TEXT NOT NULL,
                saved_recipe_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (saved_recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
            )
        ''')
        
        # Check if saved_recipe_id column exists in generated_recipes
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'generated_recipes'
            AND column_name = 'saved_recipe_id'
        """, (app.config['MYSQL_DB'],))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE generated_recipes ADD COLUMN saved_recipe_id INT")
            cursor.execute("ALTER TABLE generated_recipes ADD FOREIGN KEY (saved_recipe_id) REFERENCES recipes(id) ON DELETE SET NULL")
        
        # Create nutrition_analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nutrition_analysis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255),
                ingredients TEXT NOT NULL,
                analysis TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Check if name column exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'nutrition_analysis'
            AND column_name = 'name'
        """, (app.config['MYSQL_DB'],))

        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE nutrition_analysis ADD COLUMN name VARCHAR(255)")

        # Create grocery_list table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grocery_list (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                quantity VARCHAR(100),
                is_checked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create diet_plans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diet_plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                plan_name VARCHAR(255) NOT NULL,
                goal VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create diet_plan_meals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diet_plan_meals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                diet_plan_id INT NOT NULL,
                day INT NOT NULL,
                meal_type VARCHAR(255) NOT NULL,
                recipe_id INT,
                meal_name VARCHAR(255),
                description TEXT,
                ingredients TEXT,
                prep_time VARCHAR(255),
                FOREIGN KEY (diet_plan_id) REFERENCES diet_plans(id) ON DELETE CASCADE,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
            )
        ''')

        # Create user_allergies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_allergies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                allergy VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create meal_tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meal_tracking (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                diet_plan_meal_id INT NOT NULL,
                status ENUM('Completed', 'Skipped') NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (diet_plan_meal_id) REFERENCES diet_plan_meals(id) ON DELETE CASCADE
            )
        ''')

        # Create weight_tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weight_tracking (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                weight DECIMAL(5, 2) NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create recipe_reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipe_reviews (
                id INT AUTO_INCREMENT PRIMARY KEY,
                recipe_id INT NOT NULL,
                user_id INT NOT NULL,
                rating INT NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(recipe_id, user_id)
            )
        ''')

        # Create recipe_views table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipe_views (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                recipe_id INT NOT NULL,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                UNIQUE(user_id, recipe_id)
            )
        ''')
        
        connection.commit()
        cursor.close()
        connection.close()

# Initialize database on app start
init_db()

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Helper function to get user info
def get_user_info(user_id):
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        return user
    return None

def call_gemini_api(prompt, model=None):
    app.logger.info(f"Calling Gemini API with prompt: {prompt[:100]}...")

    # Streaming is more robust for long responses.
    try:
        if app.config['GEMINI_API_KEY'] == 'your-secret-key-here':
            app.logger.warning("Using default Gemini API key...")

        if model is None:
            model = app.config['GEMINI_TEXT_MODEL']
        
        genai_model = genai.GenerativeModel(model)
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_k=40,
            top_p=0.95,
            max_output_tokens=8192, # Increased token limit
        )

        # Use streaming to handle potentially long responses
        response_stream = genai_model.generate_content(prompt, generation_config=generation_config, stream=True)
        
        full_response_text = ""
        for chunk in response_stream:
            # The 'text' attribute may not be present on all chunks
            if hasattr(chunk, 'text'):
                full_response_text += chunk.text
        
        return full_response_text

    except Exception as e:
        app.logger.error(f"Error calling Gemini API: {e}")
        return f"Sorry, I encountered an error: {str(e)}"

def clean_json_response(response_text):
    """Cleans the Gemini API response to extract a valid JSON object."""
    # Find the first '{' and the last '}'
    start_index = response_text.find('{')
    end_index = response_text.rfind('}')
    
    if start_index != -1 and end_index != -1 and end_index > start_index:
        json_str = response_text[start_index:end_index+1]
        
        # Attempt to fix common JSON errors, like trailing commas
        json_str = re.sub(r",[ \t\r\n]*]", "]", json_str)
        json_str = re.sub(r",[ \t\r\n]*}}", "}", json_str)
        
        try:
            # Validate if it's a valid JSON
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass # Fallback to regex if simple slicing fails

    # Fallback to regex if the above fails
    match = re.search(r'{{.*}}', response_text, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Also fix trailing commas in the regex-extracted string
        json_str = re.sub(r",[ \t\r\n]*]", "]", json_str)
        json_str = re.sub(r",[ \t\r\n]*}}", "}", json_str)
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            return None # Still fails after cleaning
    
    return None

# Routes
@app.route('/')
def index():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM recipes ORDER BY created_at DESC LIMIT 6')
        featured_recipes = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('index.html', featured_recipes=featured_recipes)
    return render_template('index.html', featured_recipes=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if user and check_password_hash(user.get('password_hash', ''), password):
                if user['is_2fa_enabled']:
                    session['temp_user_id'] = user['id']
                    return redirect(url_for('verify_2fa_login'))
                else:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['is_admin'] = user['is_admin']
                    session.permanent = True
                    
                    # Check if user was trying to access a specific feature before login
                    next_page = session.pop('next', None)
                    
                    if user['is_admin']:
                        flash('Admin login successful!', 'success')
                        if next_page:
                            return redirect(next_page)
                        return redirect(url_for('admin_dashboard'))
                    else:
                        flash('Login successful!', 'success')
                        if next_page:
                            return redirect(next_page)
                        return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
                    (username, email, hashed_password)
                )
                connection.commit()
                flash('Registration successful. Please log in.', 'success')
                return redirect(url_for('login'))
            except Error as e:
                app.logger.error(f"Error during registration: {e}")
                flash('Username or email already exists', 'danger')
            finally:
                cursor.close()
                connection.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    cooking_time = request.args.get('cooking_time', '')
    difficulty = request.args.get('difficulty', '')
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        sql = 'SELECT * FROM recipes WHERE 1=1'
        params = []
        
        if query:
            sql += ' AND (title LIKE %s OR ingredients LIKE %s)'
            params.extend([f'%{query}%', f'%{query}%'])
        
        if category:
            sql += ' AND category = %s'
            params.append(category)
        
        if cooking_time:
            sql += ' AND cooking_time <= %s'
            params.append(int(cooking_time))
        
        if difficulty:
            sql += ' AND difficulty = %s'
            params.append(difficulty)
        
        sql += ' ORDER BY created_at DESC'
        
        cursor.execute(sql, params)
        recipes = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return render_template('search_results.html', recipes=recipes, query=query)
    
    return render_template('search_results.html', recipes=[], query=query)

@app.route('/recipe/<int:recipe_id>')
@login_required
def recipe_detail(recipe_id):
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM recipes WHERE id = %s', (recipe_id,))
        recipe = cursor.fetchone()

        is_favorite = False
        if 'user_id' in session:
            cursor.execute('SELECT id FROM favorites WHERE user_id = %s AND recipe_id = %s',
                          (session['user_id'], recipe_id))
            is_favorite = cursor.fetchone() is not None

            # Record the view
            cursor.execute('INSERT INTO recipe_views (user_id, recipe_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE viewed_at = CURRENT_TIMESTAMP',
                          (session['user_id'], recipe_id))

        if recipe:
            # Decode JSON fields before passing to template
            if recipe.get('nutritional_info') and isinstance(recipe['nutritional_info'], str):
                try:
                    recipe['nutritional_info'] = json.loads(recipe['nutritional_info'])
                except (json.JSONDecodeError, TypeError):
                    recipe['nutritional_info'] = {}

            if recipe.get('ingredients') and isinstance(recipe['ingredients'], str):
                try:
                    # Handle JSON string list
                    if recipe['ingredients'].strip().startswith('['):
                        recipe['ingredients'] = json.loads(recipe['ingredients'])
                    else:
                        # Handle comma-separated string as fallback
                        recipe['ingredients'] = [i.strip() for i in recipe['ingredients'].split(',') if i.strip()]
                except (json.JSONDecodeError, TypeError):
                    recipe['ingredients'] = []
            
            # Clean up newlines in ingredients and merge short items
            if recipe.get('ingredients') and isinstance(recipe['ingredients'], list):
                cleaned = []
                i = 0
                while i < len(recipe['ingredients']):
                    ing = recipe['ingredients'][i].replace('\n', ' ').replace('\r', '').strip()
                    # Keep merging with next items if they don't look like a new ingredient
                    while i + 1 < len(recipe['ingredients']):
                        next_ing = recipe['ingredients'][i + 1].strip()
                        # Check if next item looks like a NEW ingredient (starts with digit or has quantity words at start)
                        looks_like_new = (
                            next_ing and len(next_ing) > 0 and
                            (next_ing[0].isdigit() or 
                             any(next_ing.lower().startswith(q) for q in ['1 ', '2 ', '3 ', '4 ', '5 ', '6 ', '7 ', '8 ', '9 ', '0.', '1/', '2/', '1.5']))
                        )
                        if not looks_like_new:
                            # Continuation - merge it
                            ing = ing + ' ' + next_ing.replace('\n', ' ').replace('\r', '').strip()
                            i += 1
                        else:
                            break
                    if ing:
                        cleaned.append(ing)
                    i += 1
                recipe['ingredients'] = cleaned

            if recipe.get('instructions') and isinstance(recipe['instructions'], str):
                try:
                    recipe['instructions'] = json.loads(recipe['instructions'])
                except (json.JSONDecodeError, TypeError):
                    # Fallback for plain text instructions separated by newlines
                    recipe['instructions'] = [step.strip() for step in recipe['instructions'].split('\n') if step.strip()]

            # Fetch reviews and calculate average rating
            cursor.execute("SELECT rr.*, u.username FROM recipe_reviews rr JOIN users u ON rr.user_id = u.id WHERE rr.recipe_id = %s ORDER BY rr.created_at DESC", (recipe_id,))
            reviews = cursor.fetchall()

            average_rating = 0
            if reviews:
                total_rating = sum([review['rating'] for review in reviews])
                average_rating = total_rating / len(reviews)

            # Get user's rating if logged in
            user_rating = None
            if 'user_id' in session:
                cursor.execute("SELECT rating FROM recipe_reviews WHERE recipe_id = %s AND user_id = %s", (recipe_id, session['user_id']))
                user_review = cursor.fetchone()
                if user_review:
                    user_rating = user_review['rating']

            cursor.close()
            connection.close()
            return render_template('recipe_detail.html', recipe=recipe, is_favorite=is_favorite, reviews=reviews, average_rating=average_rating, user_rating=user_rating)
        else:
            cursor.close()
            connection.close()
            flash('Recipe not found', 'danger')
            return redirect(url_for('index'))
    else: # if connection is None
        flash('Recipe not found', 'danger') # Or a more specific error message
        return redirect(url_for('index'))

@app.route('/submit_review/<int:recipe_id>', methods=['POST'])
def submit_review(recipe_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to submit a review'}), 401

    user_id = session['user_id']
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    # Validate rating
    try:
        rating = int(rating) if rating and rating != 'undefined' else None
    except ValueError:
        rating = None

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            # Check if review exists
            cursor.execute("SELECT id, rating, comment FROM recipe_reviews WHERE recipe_id = %s AND user_id = %s", (recipe_id, user_id))
            existing = cursor.fetchone()

            if existing:
                # Update existing review
                if rating and rating > 0:
                    # Update rating, and comment only if provided
                    if comment and comment.strip():
                        cursor.execute("UPDATE recipe_reviews SET rating = %s, comment = %s WHERE recipe_id = %s AND user_id = %s",
                                       (rating, comment, recipe_id, user_id))
                    else:
                        cursor.execute("UPDATE recipe_reviews SET rating = %s WHERE recipe_id = %s AND user_id = %s",
                                       (rating, recipe_id, user_id))
                else:
                    # Update only comment
                    cursor.execute("UPDATE recipe_reviews SET comment = %s WHERE recipe_id = %s AND user_id = %s",
                                   (comment, recipe_id, user_id))
            else:
                # New review - require rating
                if not rating or rating <= 0:
                    return jsonify({'error': 'Rating is required for new reviews'}), 400
                cursor.execute("INSERT INTO recipe_reviews (recipe_id, user_id, rating, comment) VALUES (%s, %s, %s, %s)",
                               (recipe_id, user_id, rating, comment or ''))

            connection.commit()
            return jsonify({'status': 'success'})
        except Error as e:
            connection.rollback()
            app.logger.error(f"Error submitting review: {e}")
            return jsonify({'error': 'Error submitting review.'}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Database connection failed'}), 500


@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        flash('Please log in as a user to access this page', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cache_key = f"user_dashboard_{user_id}"
    cached_data = get_from_cache(cache_key)

    if cached_data:
        return render_template('user/dashboard.html', **cached_data)

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT r.* FROM recipes r
            JOIN favorites f ON r.id = f.recipe_id
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
            LIMIT 5
        ''', (user_id,))
        favorite_recipes = cursor.fetchall()

        cursor.execute('''
            SELECT r.* FROM recipes r
            JOIN recipe_views rv ON r.id = rv.recipe_id
            WHERE rv.user_id = %s AND rv.viewed_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY rv.viewed_at DESC
            LIMIT 5
        ''', (user_id,))
        recent_recipes = cursor.fetchall()

        cursor.execute('SELECT COUNT(*) as count FROM recipe_views WHERE user_id = %s AND viewed_at > DATE_SUB(NOW(), INTERVAL 30 DAY)', (user_id,))
        recipes_viewed_count = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM meal_plans WHERE user_id = %s', (user_id,))
        meal_plans_count = cursor.fetchone()['count']

        # Active Diet Plan Summary
        active_plan = None
        cursor.execute("SELECT * FROM diet_plans WHERE user_id = %s AND is_active = TRUE", (user_id,))
        active_plan_data = cursor.fetchone()
        if active_plan_data:
            active_plan = active_plan_data
            # Calculate adherence and streak for active plan
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)

            cursor.execute("SELECT COUNT(*) as total_meals FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id IN (SELECT id FROM diet_plan_meals WHERE diet_plan_id = %s) AND date BETWEEN %s AND %s", (user_id, active_plan['id'], start_of_week, end_of_week))
            total_meals = cursor.fetchone()['total_meals']

            cursor.execute("SELECT COUNT(*) as completed_meals FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id IN (SELECT id FROM diet_plan_meals WHERE diet_plan_id = %s) AND status = 'Completed' AND date BETWEEN %s AND %s", (user_id, active_plan['id'], start_of_week, end_of_week))
            completed_meals = cursor.fetchone()['completed_meals']

            active_plan['adherence'] = int((completed_meals / total_meals) * 100) if total_meals > 0 else 0

            cursor.execute("SELECT date FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id IN (SELECT id FROM diet_plan_meals WHERE diet_plan_id = %s) AND status = 'Completed' ORDER BY date DESC", (user_id, active_plan['id']))
            completed_dates = [row['date'] for row in cursor.fetchall()]
            
            streak = 0
            if completed_dates:
                streak = 1
                for i in range(len(completed_dates) - 1):
                    if (completed_dates[i] - completed_dates[i+1]).days == 1:
                        streak += 1
                    else:
                        break
            active_plan['streak'] = streak


        
        cursor.close()
        connection.close()

        data_to_cache = {
            'favorite_recipes': favorite_recipes,
            'recent_recipes': recent_recipes,
            'active_plan': active_plan,
            'recipes_viewed_count': recipes_viewed_count,
            'meal_plans_count': meal_plans_count
        }
        set_to_cache(cache_key, data_to_cache)

        return render_template('user/dashboard.html', **data_to_cache)
    
    return render_template('user/dashboard.html')

@app.route('/user/favorites')
def user_favorites():
    if 'user_id' not in session or session.get('is_admin'):
        flash('Please log in as a user to access this page', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('''
            SELECT r.* FROM recipes r
            JOIN favorites f ON r.id = f.recipe_id
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
        ''', (user_id,))
        favorite_recipes = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return render_template('user/favorites.html', favorite_recipes=favorite_recipes)
    
    return render_template('user/favorites.html', favorite_recipes=[])

@app.route('/toggle_favorite/<int:recipe_id>', methods=['POST'])
def toggle_favorite(recipe_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to add favorites'}), 401
    
    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        cursor.execute('SELECT id FROM favorites WHERE user_id = %s AND recipe_id = %s', 
                      (user_id, recipe_id))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('DELETE FROM favorites WHERE user_id = %s AND recipe_id = %s', 
                          (user_id, recipe_id))
            action = 'removed'
        else:
            cursor.execute('INSERT INTO favorites (user_id, recipe_id) VALUES (%s, %s)', 
                          (user_id, recipe_id))
            action = 'added'
        
        connection.commit()

        # Invalidate dashboard cache for this user
        cache_key = f"user_dashboard_{user_id}"
        with db_cache_lock:
            db_cache.pop(cache_key, None)

        cursor.close()
        connection.close()

        return jsonify({'status': 'success', 'action': action})
    
    return jsonify({'error': 'Database error'}), 500

@app.route('/check_favorite/<int:recipe_id>', methods=['GET'])
def check_favorite(recipe_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('SELECT id FROM favorites WHERE user_id = %s AND recipe_id = %s', 
                      (user_id, recipe_id))
        is_favorite = cursor.fetchone() is not None
        cursor.close()
        connection.close()
        return jsonify({'status': 'success', 'is_favorite': is_favorite})
    
    return jsonify({'error': 'Database error'}), 500

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to access this page', 'danger')
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute('SELECT COUNT(*) as count FROM users')
        user_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM recipes')
        recipe_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM favorites')
        favorite_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT * FROM recipes ORDER BY created_at DESC LIMIT 5')
        recent_recipes = cursor.fetchall()
        
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT 5')
        recent_users = cursor.fetchall()

        # User Registration Trends
        cursor.execute('SELECT DATE(created_at) as date, COUNT(*) as count FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(created_at) ORDER BY date')
        user_stats = cursor.fetchall()
        
        # Recipe Creation Trends
        cursor.execute('SELECT DATE(created_at) as date, COUNT(*) as count FROM recipes WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(created_at) ORDER by date')
        recipe_stats = cursor.fetchall()
        
        # Most Popular Categories
        cursor.execute('SELECT category, COUNT(*) as count FROM recipes GROUP BY category ORDER BY count DESC LIMIT 10')
        category_stats = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('admin/dashboard.html', 
                              user_count=user_count, 
                              recipe_count=recipe_count, 
                              favorite_count=favorite_count,
                              recent_recipes=recent_recipes,
                              recent_users=recent_users,
                              user_stats=user_stats,
                              recipe_stats=recipe_stats,
                              category_stats=category_stats)
    
    return render_template('admin/dashboard.html')

@app.route('/admin/manage_recipes')
def manage_recipes():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to access this page', 'danger')
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of recipes per page
    offset = (page - 1) * per_page

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)

        # Get total number of recipes
        cursor.execute('SELECT COUNT(*) as total FROM recipes')
        total_recipes = cursor.fetchone()['total']
        total_pages = (total_recipes + per_page - 1) // per_page  # Ceiling division

        # Calculate pagination range
        start_page = max(1, page - 2)
        end_page = min(total_pages + 1, page + 3)

        # Get recipes for the current page
        cursor.execute('SELECT * FROM recipes ORDER BY created_at DESC LIMIT %s OFFSET %s', (per_page, offset))
        recipes = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/manage_recipes.html', recipes=recipes, page=page, total_pages=total_pages, per_page=per_page, start_page=start_page, end_page=end_page)

    return render_template('admin/manage_recipes.html', recipes=[], page=page, total_pages=0, per_page=per_page)

@app.route('/admin/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to access this page', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']
        cooking_time = request.form.get('cooking_time')
        difficulty = request.form.get('difficulty')
        category = request.form.get('category')
        
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                try:
                    file.save(filepath)
                    image_url = unique_filename
                except Exception as e:
                    flash(f'Error saving image: {str(e)}', 'danger')
            elif file and file.filename and not allowed_file(file.filename):
                flash('Invalid image file type.', 'danger')

        nutritional_prompt = f"""
        Generate nutritional information for this recipe:
        Title: {title}
        Ingredients: {ingredients}
        
        Please provide the information in JSON format with these fields:
        - calories, protein (in grams), carbohydrates (in grams), fat (in grams), fiber (in grams), sugar (in grams), sodium (in milligrams)
        
        Only return the JSON, no additional text.
        """
        
        nutritional_info_raw = call_gemini_api(nutritional_prompt)
        nutritional_info_json = clean_json_response(nutritional_info_raw)
        
        if nutritional_info_json:
            try:
                # Validate and re-serialize
                nutritional_data = json.loads(nutritional_info_json)
                nutritional_info = json.dumps(nutritional_data)
            except json.JSONDecodeError:
                nutritional_info = None
        else:
            nutritional_info = None

        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO recipes (title, ingredients, instructions, cooking_time, difficulty, category, image_url, nutritional_info, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (title, ingredients, instructions, cooking_time, difficulty, category, image_url, nutritional_info, session['user_id']))
            connection.commit()
            cursor.close()
            connection.close()
            
            flash('Recipe added successfully', 'success')
            return redirect(url_for('manage_recipes'))
    
    return render_template('admin/edit_recipe.html', recipe=None)

@app.route('/admin/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to access this page', 'danger')
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if not connection:
        flash('Database connection failed', 'danger')
        return redirect(url_for('manage_recipes'))

    if request.method == 'POST':
        title = request.form['title']
        ingredients = request.form['ingredients']
        instructions = request.form['instructions']
        cooking_time = request.form.get('cooking_time')
        difficulty = request.form.get('difficulty')
        category = request.form.get('category')
        
        image_url = request.form.get('current_image')
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                try:
                    file.save(filepath)
                    image_url = unique_filename
                except Exception as e:
                    flash(f'Error saving image: {str(e)}', 'danger')
            elif file and file.filename and not allowed_file(file.filename):
                flash('Invalid image file type.', 'danger')
        
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE recipes 
            SET title = %s, ingredients = %s, instructions = %s, cooking_time = %s, 
                difficulty = %s, category = %s, image_url = %s
            WHERE id = %s
        """, (title, ingredients, instructions, cooking_time, difficulty, category, image_url, recipe_id))
        connection.commit()
        cursor.close()
        connection.close()
        
        flash('Recipe updated successfully', 'success')
        return redirect(url_for('manage_recipes'))
    
    else:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM recipes WHERE id = %s', (recipe_id,))
        recipe = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if recipe:
            return render_template('admin/edit_recipe.html', recipe=recipe)
        else:
            flash('Recipe not found', 'danger')
            return redirect(url_for('manage_recipes'))

@app.route('/admin/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM recipes WHERE id = %s', (recipe_id,))
        connection.commit()
        cursor.close()
        connection.close()
        
        flash('Recipe deleted successfully', 'success')
        return jsonify({'status': 'success'})
    
    return jsonify({'error': 'Database error'}), 500

@app.route('/admin/manage_users')
def manage_users():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to access this page', 'danger')
        return redirect(url_for('login'))

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        cursor.close()
        connection.close()

        return render_template('admin/manage_users.html', users=users)

    return render_template('admin/manage_users.html', users=[])

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to access this page', 'danger')
        return redirect(url_for('login'))

    connection = get_db_connection()
    if not connection:
        flash('Database connection failed', 'danger')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        is_admin = 'is_admin' in request.form

        cursor = connection.cursor()
        cursor.execute("UPDATE users SET username = %s, email = %s, is_admin = %s WHERE id = %s",
                       (username, email, is_admin, user_id))
        connection.commit()
        cursor.close()
        connection.close()

        flash('User updated successfully', 'success')
        return redirect(url_for('manage_users'))

    else:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user:
            return render_template('admin/edit_user.html', user=user)
        else:
            flash('User not found', 'danger')
            return redirect(url_for('manage_users'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        connection.commit()
        cursor.close()
        connection.close()

        flash('User deleted successfully', 'success')
        return redirect(url_for('manage_users'))

    return jsonify({'error': 'Database error'}), 500

@app.route('/admin/stats')
def admin_stats():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to access this page', 'danger')
        return redirect(url_for('login'))

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute('SELECT DATE(created_at) as date, COUNT(*) as count FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(created_at) ORDER BY date')
        user_stats = cursor.fetchall()

        cursor.execute('SELECT DATE(created_at) as date, COUNT(*) as count FROM recipes WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(created_at) ORDER by date')
        recipe_stats = cursor.fetchall()

        cursor.execute('SELECT category, COUNT(*) as count FROM recipes GROUP BY category ORDER BY count DESC LIMIT 10')
        category_stats = cursor.fetchall()

        # Fetch recent reviews for admin stats
        cursor.execute('''
            SELECT rr.id, rr.rating, rr.comment, rr.created_at, u.username, r.title as recipe_title
            FROM recipe_reviews rr
            JOIN users u ON rr.user_id = u.id
            JOIN recipes r ON rr.recipe_id = r.id
            ORDER BY rr.created_at DESC
            LIMIT 20
        ''')
        reviews = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('admin/stats.html',
                              user_stats=user_stats,
                              recipe_stats=recipe_stats,
                              category_stats=category_stats,
                              reviews=reviews)

    return render_template('admin/stats.html')

@app.route('/admin/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM recipe_reviews WHERE id = %s', (review_id,))
        connection.commit()
        cursor.close()
        connection.close()

        flash('Review deleted successfully', 'success')
        return redirect(url_for('admin_stats'))

    return jsonify({'error': 'Database error'}), 500

@app.route('/chatbot', methods=['GET', 'POST'])
@login_required
def chatbot():
    app.logger.info(f"Chatbot route accessed, method: {request.method}")

    if request.method == 'POST':
        message = request.json.get('message', '')
        app.logger.info(f"Chatbot POST request with message: {message}")

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        prompt = f'''You are a helpful Recipe Assistant. Your goal is to provide clear and simple cooking instructions.

When a user asks for a recipe, you must provide:
1.  A list of ingredients.
2.  The step-by-step method for preparing the dish.

Use simple, easy-to-understand language. Do not use any special formatting like asterisks, bullet points, or hash symbols. Just use plain text and paragraphs.

For example, if the user asks for "pancakes", a good response would be:

To make pancakes, you will need these ingredients:
1 cup of all-purpose flour
2 tablespoons of sugar
2 teaspoons of baking powder
1/2 teaspoon of salt
1 cup of milk
1 egg
2 tablespoons of melted butter

Here is the method to make them:
First, in a large bowl, mix together the flour, sugar, baking powder, and salt.
In another bowl, whisk together the milk and egg.
Pour the wet ingredients into the dry ingredients and stir until just combined. Do not overmix.
Stir in the melted butter.
Heat a lightly oiled griddle or frying pan over medium-high heat.
Pour or scoop the batter onto the griddle, using approximately 1/4 cup for each pancake.
Cook until bubbles appear on the surface, then flip and cook until browned on the other side.

The user asked: "{message}"'''

        response_text = call_gemini_api(prompt)

        # Clean the response to remove any markdown-like formatting
        response_text = response_text.replace('*', '').replace('#', '')

        if 'user_id' in session:
            try:
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute('INSERT INTO chat_history (user_id, message, response) VALUES (%s, %s, %s)', (session['user_id'], message, response_text))
                    connection.commit()
                    cursor.close()
                    connection.close()
            except Error as e:
                app.logger.error(f"Database error in chatbot: {e}")

        return jsonify({'response': response_text})

    return render_template('chatbot.html')

@app.route('/nutrition_helper', methods=['GET', 'POST'])
@login_required
def nutrition_helper():
    app.logger.info(f"Nutrition helper route accessed, method: {request.method}")

    ingredients_text = ''
    analysis = None
    analysis_history = []

    # GET request - show history if logged in
    if 'user_id' in session:
        user_id = session['user_id']
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute('SELECT * FROM nutrition_analysis WHERE user_id = %s ORDER BY created_at DESC LIMIT 5', (user_id,))
                analysis_history = cursor.fetchall()
                cursor.close()
            except Error as e:
                app.logger.error(f"Database error fetching nutrition history: {e}")
            finally:
                connection.close()

    if request.method == 'POST':
        ingredients_text = request.form.get('ingredients', '')
        app.logger.info(f"Nutrition helper POST request with ingredients: {ingredients_text}")

        if not ingredients_text:
            return jsonify({'error': 'Please enter some ingredients'}), 400

        prompt = f'Analyze the nutritional content of these ingredients: {ingredients_text}\n\nProvide a detailed breakdown including: 1. Estimated total calories, 2. Macronutrients (protein, carbs, fat), 3. Key vitamins and minerals, 4. Health benefits, 5. Potential concerns or allergies. Format your response in HTML with headings and bullet points.'

        analysis = call_gemini_api(prompt)

        if analysis:
            analysis = re.sub(r'```[a-z]*\n|```', '', analysis).strip()
            if not analysis.startswith('<'):
                analysis = f'<div class="nutrition-analysis"><p>{analysis}</p></div>'

        if analysis and not analysis.startswith("Sorry"):
            # Analysis is generated, but saving is handled by the save button
            pass

        # Render template with the analysis results instead of redirecting
        return render_template('nutrition_helper.html',
                             analysis_history=analysis_history,
                             ingredients=ingredients_text,
                             analysis=analysis)

    # GET request - just show the form with history
    return render_template('nutrition_helper.html',
                         analysis_history=analysis_history,
                         ingredients=ingredients_text,
                         analysis=analysis)

@app.route('/meal_planner', methods=['GET', 'POST'])
@login_required
def meal_planner():
    app.logger.info(f"Meal planner route accessed, method: {request.method}")

    user_id = None
    if 'user_id' in session:
        user_id = session['user_id']
    
    if request.method == 'POST':
        dietary_preferences = request.form.get('dietary_preferences', '')
        allergies = request.form.get('allergies', '')
        days = int(request.form.get('days', 7))
        app.logger.info(f"Meal planner POST request with prefs: {dietary_preferences}, allergies: {allergies}, days: {days}")
        
        prompt = f"""
        Create a {days}-day meal plan with the following requirements:
        - Dietary preferences: {dietary_preferences}
        - Allergies: {allergies}

        IMPORTANT: You must generate exactly {days} days in the meal plan. Each day must have a unique day name like "Day 1", "Day 2", up to "Day {days}".

        Format your response as a JSON object with a single key "days".
        The value of "days" should be a list of exactly {days} day objects.
        Each day object should have a "day" name (e.g., "Day 1") and a list of "meals".
        Each meal object should have "type", "name", "description", "ingredients" (as a list of strings), and "prep_time".

        Example format:
        {{
          "days": [
            {{
              "day": "Day 1",
              "meals": [
                {{
                  "type": "Breakfast",
                  "name": "Oatmeal",
                  "description": "...",
                  "ingredients": ["1 cup oats", "2 cups milk"],
                  "prep_time": "5 minutes"
                }}
              ]
            }}
          ]
        }}

        Only return the JSON object, with no additional text or markdown.
        """
        
        raw_response = call_gemini_api(prompt)
        
        if raw_response.startswith("Sorry"):
            flash(raw_response, 'danger')
            return render_template('meal_planner.html', form_data=request.form)

        meal_plan_json = clean_json_response(raw_response)

        if not meal_plan_json:
            flash("Sorry, the AI returned an invalid format. Please try again.", 'danger')
            app.logger.error(f"Meal Plan Clean Error: Could not extract JSON from response: {raw_response}")
            return render_template('meal_planner.html', form_data=request.form)

        try:
            meal_plan_nested = json.loads(meal_plan_json)

            # The user wants to see the generated meal plan on the meal_planner page,
            # not a diet plan page. We pass the generated plan to the template.
            
            # We also need to fetch saved plans to display them.
            saved_plans = []
            if user_id:
                connection = get_db_connection()
                if connection:
                    try:
                        cursor = connection.cursor(dictionary=True)
                        cursor.execute('SELECT * FROM meal_plans WHERE user_id = %s ORDER BY created_at DESC LIMIT 5', (user_id,))
                        saved_plans = cursor.fetchall()

                        for plan in saved_plans:
                            try:
                                if plan['plan_data']:
                                    plan['plan_data'] = json.loads(plan['plan_data'])
                            except (json.JSONDecodeError, TypeError) as e:
                                app.logger.error(f"Error parsing saved plan data: {e}")
                                plan['plan_data'] = None

                        cursor.close()
                    except Error as e:
                        app.logger.error(f"Database error fetching meal plans: {e}")
                    finally:
                        connection.close()

            return render_template('meal_planner.html', meal_plan=meal_plan_nested, form_data=request.form, saved_plans=saved_plans)

        except (json.JSONDecodeError, ValueError, Error) as e:
            error_message = f"Error processing meal plan: {str(e)}"
            if isinstance(e, json.JSONDecodeError) or isinstance(e, ValueError):
                error_message = "Sorry, the AI returned an invalid format. Please try again."
                app.logger.error(f"JSON Parse Error: {e}\nResponse was: {meal_plan_json}")
            
            flash(error_message, 'danger')
            
            # Also fetch saved plans here to render the page correctly on error
            connection = get_db_connection()
            saved_plans = []
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)
                    cursor.execute('SELECT * FROM meal_plans WHERE user_id = %s ORDER BY created_at DESC LIMIT 5', (user_id,))
                    saved_plans = cursor.fetchall()
                    
                    for plan in saved_plans:
                        try:
                            if plan['plan_data']:
                                plan['plan_data'] = json.loads(plan['plan_data'])
                        except (json.JSONDecodeError, TypeError) as e:
                            app.logger.error(f"Error parsing saved plan data: {e}")
                            plan['plan_data'] = None
                    
                    cursor.close()
                except Error as e:
                    app.logger.error(f"Database error fetching meal plans: {e}")
                finally:
                    connection.close()
            return render_template('meal_planner.html', form_data=request.form, saved_plans=saved_plans)
    
    # GET request - show saved plans
    saved_plans = []
    if user_id:
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute('SELECT * FROM meal_plans WHERE user_id = %s ORDER BY created_at DESC LIMIT 5', (user_id,))
                saved_plans = cursor.fetchall()

                for plan in saved_plans:
                    try:
                        if plan['plan_data']:
                            plan['plan_data'] = json.loads(plan['plan_data'])
                    except (json.JSONDecodeError, TypeError) as e:
                        app.logger.error(f"Error parsing saved plan data: {e}")
                        plan['plan_data'] = None

                cursor.close()
            except Error as e:
                app.logger.error(f"Database error fetching meal plans: {e}")
                flash('Error loading saved meal plans', 'danger')
            finally:
                connection.close()

    return render_template('meal_planner.html', saved_plans=saved_plans, form_data={})

@app.route('/meal_plan_detail/<int:plan_id>')
def meal_plan_detail(plan_id):
    if 'user_id' not in session:
        flash('Please log in to view meal plans', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM meal_plans WHERE id = %s AND user_id = %s', (plan_id, user_id))
        plan = cursor.fetchone()
        cursor.close()
        connection.close()

        if plan:
            try:
                plan['plan_data'] = json.loads(plan['plan_data'])
                # Extract plan_name and goal to top level for template
                plan['plan_name'] = plan['plan_data'].get('plan_name', 'Meal Plan')
                plan['goal'] = plan['plan_data'].get('goal', 'Custom Goal')
                # If plan_data has 'days', use it; else group meals by day
                if 'days' not in plan['plan_data'] and 'meals' in plan['plan_data']:
                    days = {}
                    for meal in plan['plan_data']['meals']:
                        day = meal.get('day', 'Day 1')
                        if day not in days:
                            days[day] = []
                        days[day].append(meal)
                    plan['plan_data']['days'] = [{'day': day, 'meals': meals} for day, meals in days.items()]
                return render_template('meal_plan_detail.html', meal_plan=plan)
            except json.JSONDecodeError:
                flash('Error loading meal plan data', 'danger')
                return redirect(url_for('meal_planner'))
        else:
            flash('Meal plan not found', 'danger')
            return redirect(url_for('meal_planner'))

    return redirect(url_for('meal_planner'))

@app.route('/save_meal_plan', methods=['POST'])
def save_meal_plan():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to save meal plans'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    plan_name = data.get('plan_name')
    goal = data.get('goal')
    meals = data.get('meals')

    if not plan_name or not goal or not meals:
        return jsonify({'error': 'Missing plan data fields'}), 400

    plan_data_json = json.dumps({'plan_name': plan_name, 'goal': goal, 'meals': meals})

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO meal_plans (user_id, plan_data) VALUES (%s, %s)', (user_id, plan_data_json))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'status': 'success', 'message': 'Meal plan saved successfully!'})

    return jsonify({'error': 'Database error'}), 500

@app.route('/delete_meal_plan/<int:plan_id>', methods=['POST'])
def delete_meal_plan(plan_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to delete meal plans'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM meal_plans WHERE id = %s AND user_id = %s', (plan_id, user_id))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'status': 'success', 'message': 'Meal plan deleted successfully!'})

    return jsonify({'error': 'Database error'}), 500

@app.route('/generate_recipe_image', methods=['POST'])
def generate_recipe_image_endpoint():
    """
    Generate recipe image using Bytez AI
    Accepts JSON with prompt, ingredients, and optional logo
    """
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        ingredients = data.get("ingredients", "")
        logo_base64 = data.get("logo_file", None)

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        # Handle logo if provided
        logo_path = None
        if logo_base64:
            try:
                # Save logo temporarily
                logo_bytes = base64.b64decode(logo_base64.split(',')[1] if ',' in logo_base64 else logo_base64)
                temp_dir = tempfile.gettempdir()
                logo_path = os.path.join(temp_dir, f"logo_{uuid4().hex}.png")
                with open(logo_path, 'wb') as f:
                    f.write(logo_bytes)
            except Exception as e:
                app.logger.warning(f"Logo processing failed: {e}")
                logo_path = None
        
        # Generate image using Bytez
        result = bytez_generator.generate_image(
            description=prompt,
            ingredients=ingredients,
            logo_path=logo_path
        )
        
        # Clean up temp logo
        if logo_path and os.path.exists(logo_path):
            try:
                os.remove(logo_path)
            except:
                pass
        
        if result['success']:
            # Copy image to upload folder
            temp_image_path = result['image_path']
            unique_filename = f"{uuid4().hex}.png"
            final_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Copy file
            import shutil
            shutil.copy2(temp_image_path, final_path)
            
            # Clean up temp file
            try:
                os.remove(temp_image_path)
            except:
                pass
            
            # Use relative URL for compatibility with port forwarding
            final_image_url = url_for('uploaded_file', filename=unique_filename)
            
            return jsonify({
                "success": True,
                "image_prompt": result.get('prompt', prompt),
                "image_url": final_image_url,
                "user": "Bytez Photoreal AI",
                "note": "Image generated by Bytez AI"
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Image generation failed')
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error during image generation: {e}")
        return jsonify({
            "success": False,
            "error": f"An error occurred: {str(e)}"
        }), 500


@app.route('/ai_recipe_generator', methods=['GET', 'POST'])
@login_required
def ai_recipe_generator():
    app.logger.info(f"AI recipe generator route accessed, method: {request.method}")

    user_id = None
    if 'user_id' in session:
        user_id = session['user_id']
    
    if request.method == 'POST':
        ingredients = request.form.get('ingredients', '')
        cuisine = request.form.get('cuisine', '')
        meal_type = request.form.get('meal_type', '')
        dietary_restrictions = request.form.get('dietary_restrictions', '')
        app.logger.info(f"AI recipe generator POST with ingredients: {ingredients}, cuisine: {cuisine}")
        
        if not ingredients:
            flash('Please enter at least some ingredients', 'danger')
            return redirect(url_for('ai_recipe_generator'))
        
        prompt = f'Create a recipe with the following requirements: - Main ingredients: {ingredients} - Cuisine style: {cuisine} - Meal type: {meal_type} - Dietary restrictions: {dietary_restrictions}. Provide the recipe in JSON format with these fields: title, description, ingredients (as a list of strings), instructions (as a list of strings), cooking_time (e.g., "30 minutes"), difficulty, category, nutritional_info (as a JSON object). Only return the JSON, no additional text.'
        
        raw_response = call_gemini_api(prompt)

        if raw_response.startswith("Sorry"):
            flash(raw_response, 'danger')
            return render_template('ai_recipe_generator.html', form_data=request.form)
        
        recipe_json = clean_json_response(raw_response)

        if not recipe_json:
            flash("Sorry, the AI returned an invalid format. Please try again.", 'danger')
            app.logger.error(f"AI Recipe Gen Clean Error: Could not extract JSON from response: {raw_response}")
            return render_template('ai_recipe_generator.html', form_data=request.form)

        try:
            recipe = json.loads(recipe_json)
            
            # Automatically generate image for the recipe
            recipe_image_url = None
            recipe_image_prompt = None
            try:
                app.logger.info(f"Auto-generating image for recipe: {recipe.get('title', 'Unknown')}")
                
                # Generate image using Bytez with optimized ingredients (max 3 for speed)
                image_result = bytez_generator.generate_image(
                    description=recipe.get('title', 'delicious food'),
                    ingredients=', '.join(recipe.get('ingredients', [])[:3]) if isinstance(recipe.get('ingredients'), list) else ''
                )
                
                if image_result['success']:
                    # Copy image to upload folder (optimized - use move instead of copy when possible)
                    temp_image_path = image_result['image_path']
                    unique_filename = f"{uuid4().hex}.png"
                    final_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    # Use move for speed, fallback to copy if on different drives
                    try:
                        shutil.move(temp_image_path, final_path)
                    except:
                        shutil.copy2(temp_image_path, final_path)
                        try:
                            os.remove(temp_image_path)
                        except:
                            pass
                    
                    # Use relative URL for compatibility with port forwarding
                    recipe_image_url = url_for('uploaded_file', filename=unique_filename)
                    recipe_image_prompt = image_result.get('prompt', '')
                    recipe['image_url'] = recipe_image_url
                    recipe['image_prompt'] = recipe_image_prompt
                    
                    app.logger.info(f"Image generated successfully: {unique_filename}")
                else:
                    app.logger.warning(f"Image generation failed: {image_result.get('error', 'Unknown error')}")
                    
            except Exception as img_error:
                app.logger.error(f"Error during auto image generation: {img_error}")
                # Continue even if image generation fails
            
            # Save the generated recipe for history (with image if available)
            generated_recipe_id = None
            connection = get_db_connection()
            if connection:
                cursor = connection.cursor()
                # The recipe object already has image_url and image_prompt if they were generated
                # Always use the current recipe object (which includes image if generated)
                updated_json = json.dumps(recipe, ensure_ascii=False)
                cursor.execute('INSERT INTO generated_recipes (user_id, prompt, recipe_data) VALUES (%s, %s, %s)', (user_id, prompt, updated_json))
                generated_recipe_id = cursor.lastrowid
                connection.commit()
                cursor.close()
                connection.close()
            
            return render_template('ai_recipe_generator.html', generated_recipe=recipe, generated_recipe_id=generated_recipe_id, form_data=request.form)
        except (json.JSONDecodeError, Error) as e:
            error_message = f"Error processing generated recipe: {str(e)}"
            if isinstance(e, json.JSONDecodeError):
                error_message = "Sorry, the AI returned an invalid format. Please try again."

            flash(error_message, 'danger')
            app.logger.error(f"AI Recipe Gen Error: {e}\nResponse was: {recipe_json}")
            return render_template('ai_recipe_generator.html', form_data=request.form)
    
    # For GET request, show history of generated recipes
    connection = get_db_connection()
    recipe_history = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            # Show all generated recipes (both saved and unsaved)
            cursor.execute('SELECT * FROM generated_recipes WHERE user_id = %s ORDER BY created_at DESC LIMIT 5', (user_id,))
            recipe_history = cursor.fetchall()
            for recipe in recipe_history:
                try:
                    recipe['recipe_data'] = json.loads(recipe['recipe_data'])
                except (json.JSONDecodeError, TypeError):
                    recipe['recipe_data'] = None
            cursor.close()
        except Error as e:
            app.logger.error(f"Database error fetching generated recipe history: {e}")
        finally:
            connection.close()

    return render_template('ai_recipe_generator.html', recipe_history=recipe_history, form_data={})

@app.route('/generated_recipe/<int:generated_recipe_id>')
def generated_recipe_detail(generated_recipe_id):
    if 'user_id' not in session:
        flash('Please log in to view this page', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT * FROM generated_recipes WHERE id = %s AND user_id = %s', (generated_recipe_id, user_id))
            generated_recipe = cursor.fetchone()

            if generated_recipe:
                # Record the view
                cursor.execute('INSERT INTO recipe_views (user_id, recipe_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE viewed_at = CURRENT_TIMESTAMP',
                              (user_id, generated_recipe_id))
                
                # Check if this recipe has been saved
                generated_recipe['is_saved'] = generated_recipe.get('saved_recipe_id') is not None

            cursor.close()

            if generated_recipe:
                try:
                    generated_recipe['recipe_data'] = json.loads(generated_recipe['recipe_data'])
                    return render_template('generated_recipe_detail.html', generated_recipe=generated_recipe)
                except (json.JSONDecodeError, TypeError):
                    flash('Error decoding recipe data.', 'danger')
                    return redirect(url_for('ai_recipe_generator'))
            else:
                flash('Generated recipe not found.', 'danger')
                return redirect(url_for('ai_recipe_generator'))
        except Error as e:
            app.logger.error(f"Database error fetching generated recipe: {e}")
            flash('Database error.', 'danger')
            return redirect(url_for('ai_recipe_generator'))
        finally:
            connection.close()
    else:
        flash('Database connection failed.', 'danger')
        return redirect(url_for('ai_recipe_generator'))


@app.route('/save_generated_recipe', methods=['POST'])
def save_generated_recipe():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to save recipes'}), 401

    recipe_json = request.form.get('recipe_data')
    image_url_to_save = request.form.get('image_url')
    image_prompt = request.form.get('image_prompt')
    audio_url_to_save = request.form.get('audio_url')

    if not recipe_json:
        return jsonify({'error': 'Recipe data is missing'}), 400

    try:
        recipe_data = json.loads(recipe_json)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid recipe data format'}), 400

    if not isinstance(recipe_data, dict):
        return jsonify({'error': 'Recipe data must be an object'}), 400

    image_url = None
    if 'recipe_image' in request.files and request.files['recipe_image'].filename != '':
        file = request.files['recipe_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            try:
                file.save(filepath)
                image_url = unique_filename
            except Exception as e:
                app.logger.error(f"Error saving uploaded image: {e}")
                return jsonify({'error': f'Error saving image: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Invalid image file type'}), 400
    elif image_url_to_save:
        # Check if it's a relative URL (already in our upload folder)
        if image_url_to_save.startswith('/uploads/'):
            # Extract just the filename from the path
            image_url = image_url_to_save.replace('/uploads/', '')
        elif image_url_to_save.startswith('http://') or image_url_to_save.startswith('https://'):
            # It's an absolute URL, download it
            try:
                response = requests.get(image_url_to_save, stream=True, timeout=30)
                response.raise_for_status()

                file_ext = os.path.splitext(urllib.parse.urlparse(image_url_to_save).path)[1]
                if not file_ext:
                    content_type = response.headers.get('content-type')
                    if content_type == 'image/png':
                        file_ext = '.png'
                    elif content_type == 'image/jpeg':
                        file_ext = '.jpg'
                    else:
                        file_ext = '.jpg'

                unique_filename = f"{uuid4().hex}{file_ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                image_url = unique_filename
            except requests.exceptions.RequestException as e:
                app.logger.error(f"Error downloading image from URL: {e}")
                return jsonify({'error': 'Could not download image from URL'}), 500
        else:
            # Assume it's just a filename
            image_url = image_url_to_save

    # Image is optional for saving generated recipes
    if not image_url:
        image_url = None

    connection = get_db_connection()
    if connection:
        try:
            ingredients = ', '.join(recipe_data.get('ingredients', []))
            instructions = '\n'.join(recipe_data.get('instructions', []))
            nutritional_info = json.dumps(recipe_data.get('nutritional_info', {}), ensure_ascii=False)

            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO recipes (title, ingredients, instructions, cooking_time, difficulty, category, image_url, image_prompt, audio_url, nutritional_info, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                recipe_data.get('title'),
                ingredients,
                instructions,
                recipe_data.get('cooking_time'),
                recipe_data.get('difficulty'),
                recipe_data.get('category'),
                image_url,
                image_prompt,
                audio_url_to_save,
                nutritional_info,
                session['user_id']
            ))
            new_recipe_id = cursor.lastrowid
            
            # Update the generated_recipe to mark it as saved (if it came from generated_recipes)
            generated_recipe_id = request.form.get('generated_recipe_id')
            if generated_recipe_id:
                cursor.execute(
                    "UPDATE generated_recipes SET saved_recipe_id = %s WHERE id = %s AND user_id = %s",
                    (new_recipe_id, generated_recipe_id, session['user_id'])
                )
            
            connection.commit()
            cursor.close()
            connection.close()

            redirect_url = url_for('recipe_detail', recipe_id=new_recipe_id)
            return jsonify({'status': 'success', 'message': 'Recipe saved successfully!', 'redirect_url': redirect_url})

        except Error as e:
            app.logger.error(f"Error saving generated recipe: {e}")
            return jsonify({'error': 'Database error while saving recipe'}), 500

    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/update_generated_recipe_image/<int:generated_recipe_id>', methods=['POST'])
def update_generated_recipe_image(generated_recipe_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to update recipes'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    image_url = data.get('image_url')
    image_prompt = data.get('image_prompt')

    if not image_url:
        return jsonify({'error': 'Image URL is required'}), 400

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT * FROM generated_recipes WHERE id = %s AND user_id = %s', (generated_recipe_id, user_id))
            generated_recipe = cursor.fetchone()

            if not generated_recipe:
                cursor.close()
                connection.close()
                return jsonify({'error': 'Generated recipe not found or you do not have permission to update it'}), 404

            # Update the recipe_data JSON with the new image_url and image_prompt
            recipe_data = json.loads(generated_recipe['recipe_data'])
            recipe_data['image_url'] = image_url
            recipe_data['image_prompt'] = image_prompt
            updated_recipe_data = json.dumps(recipe_data, ensure_ascii=False)

            cursor.execute('UPDATE generated_recipes SET recipe_data = %s WHERE id = %s', (updated_recipe_data, generated_recipe_id))
            connection.commit()
            cursor.close()
            connection.close()

            return jsonify({'status': 'success', 'message': 'Recipe image updated successfully!'})

        except Error as e:
            app.logger.error(f"Error updating generated recipe image: {e}")
            return jsonify({'error': 'Database error while updating recipe'}), 500
        except json.JSONDecodeError as e:
            app.logger.error(f"Error parsing recipe data: {e}")
            return jsonify({'error': 'Invalid recipe data format'}), 500

    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/generate_recipe_audio', methods=['POST'])
def generate_recipe_audio():
    """
    Generate text-to-speech audio for a recipe using Gemini API
    Accepts JSON with recipe title, ingredients, and instructions
    """
    try:
        data = request.get_json()
        title = data.get('title', '')
        ingredients = data.get('ingredients', [])
        instructions = data.get('instructions', [])
        generated_recipe_id = data.get('generated_recipe_id')
        
        if not title:
            return jsonify({'error': 'Recipe title is required'}), 400
        
        # Create text content for speech
        speech_text = f"Recipe: {title}. "
        
        if ingredients:
            speech_text += "Ingredients: "
            if isinstance(ingredients, list):
                speech_text += ", ".join(ingredients) + ". "
            else:
                speech_text += str(ingredients) + ". "
        
        if instructions:
            speech_text += "Instructions: "
            if isinstance(instructions, list):
                for i, step in enumerate(instructions, 1):
                    speech_text += f"Step {i}: {step}. "
            else:
                speech_text += str(instructions) + ". "
        
        # Generate audio using Google Text-to-Speech API
        try:
            from google.cloud import texttospeech
            
            # Initialize the client
            client = texttospeech.TextToSpeechClient()
            
            # Set the text input
            synthesis_input = texttospeech.SynthesisInput(text=speech_text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-F",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            
            # Select the audio file type
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Save the audio file
            unique_filename = f"{uuid4().hex}_recipe_audio.mp3"
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            with open(audio_path, 'wb') as out:
                out.write(response.audio_content)
            
            # Use relative URL for compatibility with port forwarding
            audio_url = url_for('uploaded_file', filename=unique_filename)
            
            # Update generated_recipes with audio URL if generated_recipe_id is provided
            if generated_recipe_id:
                user_id = session.get('user_id')
                connection = get_db_connection()
                if connection:
                    try:
                        cursor = connection.cursor(dictionary=True)
                        cursor.execute('SELECT * FROM generated_recipes WHERE id = %s AND user_id = %s', (generated_recipe_id, user_id))
                        generated_recipe = cursor.fetchone()
                        
                        if generated_recipe:
                            recipe_data = json.loads(generated_recipe['recipe_data'])
                            recipe_data['audio_url'] = audio_url
                            updated_recipe_data = json.dumps(recipe_data, ensure_ascii=False)
                            
                            cursor.execute('UPDATE generated_recipes SET recipe_data = %s WHERE id = %s', (updated_recipe_data, generated_recipe_id))
                            connection.commit()
                        
                        cursor.close()
                        connection.close()
                    except Exception as db_error:
                        app.logger.error(f"Error updating generated recipe with audio: {db_error}")
            
            return jsonify({
                'success': True,
                'audio_url': audio_url,
                'message': 'Audio generated successfully'
            })
            
        except Exception as tts_error:
            # Fallback: Use browser's built-in speech synthesis
            app.logger.warning(f"Google TTS failed: {tts_error}. Using browser TTS fallback.")
            return jsonify({
                'success': True,
                'use_browser_tts': True,
                'text': speech_text,
                'message': 'Using browser speech synthesis'
            })
            
    except Exception as e:
        app.logger.error(f"Error generating recipe audio: {e}")
        return jsonify({
            'success': False,
            'error': f"An error occurred: {str(e)}"
        }), 500


# --- Grocery List Routes ---
@app.route('/grocery_list')
def grocery_list():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    connection = get_db_connection()
    items = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT * FROM grocery_list WHERE user_id = %s ORDER BY created_at DESC', (user_id,))
            items = cursor.fetchall()
            cursor.close()
        except Error as e:
            app.logger.error(f"Error fetching grocery list: {e}")
            return jsonify({'error': 'Could not load your grocery list.'}), 500
        finally:
            connection.close()
            
    return render_template('grocery_list.html', items=items)

@app.route('/api/grocery_list/add', methods=['POST'])
def add_to_grocery_list():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    item_name = data.get('item_name')
    quantity = data.get('quantity', '')

    if not item_name:
        return jsonify({'error': 'Item name is required'}), 400
        
    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                'INSERT INTO grocery_list (user_id, item_name, quantity) VALUES (%s, %s, %s)',
                (user_id, item_name, quantity)
            )
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({'status': 'success', 'message': f'Added "{item_name}" to your grocery list.'})
        except Error as e:
            app.logger.error(f"Error adding to grocery list: {e}")
            return jsonify({'error': 'Database error'}), 500
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/grocery_list/add_multiple', methods=['POST'])
def add_multiple_to_grocery_list():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    items = data.get('items')

    if not items or not isinstance(items, list):
        return jsonify({'error': 'A list of items is required'}), 400
        
    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            sql = 'INSERT INTO grocery_list (user_id, item_name) VALUES (%s, %s)'
            # Filter out empty strings
            values = [(user_id, item) for item in items if item]
            if not values:
                return jsonify({'error': 'No valid items to add'}), 400
            
            cursor.executemany(sql, values)
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({'status': 'success', 'message': f'Added {len(values)} items to your grocery list.'})
        except Error as e:
            app.logger.error(f"Error adding multiple items to grocery list: {e}")
            return jsonify({'error': 'Database error'}), 500
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/grocery_list/update/<int:item_id>', methods=['POST'])
def update_grocery_item(item_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    is_checked = data.get('is_checked')

    if is_checked is None:
        return jsonify({'error': 'is_checked field is required'}), 400

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                'UPDATE grocery_list SET is_checked = %s WHERE id = %s AND user_id = %s',
                (is_checked, item_id, user_id)
            )
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({'status': 'success'})
        except Error as e:
            app.logger.error(f"Error updating grocery item: {e}")
            return jsonify({'error': 'Database error'}), 500
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/grocery_list/delete/<int:item_id>', methods=['POST'])
def delete_grocery_item(item_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute('DELETE FROM grocery_list WHERE id = %s AND user_id = %s', (item_id, user_id))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({'status': 'success'})
        except Error as e:
            app.logger.error(f"Error deleting grocery item: {e}")
            return jsonify({'error': 'Database error'}), 500
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/grocery_list/clear', methods=['POST'])
def clear_grocery_list():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute('DELETE FROM grocery_list WHERE user_id = %s', (user_id,))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({'status': 'success', 'message': 'Grocery list cleared.'})
        except Error as e:
            app.logger.error(f"Error clearing grocery list: {e}")
            return jsonify({'error': 'Database error'}), 500
    return jsonify({'error': 'Database connection failed'}), 500


@app.route('/generate_report')
def generate_report():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Please log in as an admin to generate reports', 'danger')
        return redirect(url_for('login'))

    report_type = request.args.get('type', 'users')

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)

        if report_type == 'users':
            cursor.execute('SELECT username, email, created_at FROM users ORDER BY created_at DESC')
            data = cursor.fetchall()
            title = 'Users Report'
            headers = ['Username', 'Email', 'Created At']
        elif report_type == 'recipes':
            cursor.execute('SELECT r.title, r.difficulty, r.cooking_time, r.created_at FROM recipes r ORDER BY r.created_at DESC')
            data = cursor.fetchall()
            title = 'Recipes Report'
            headers = ['Title', 'Difficulty', 'Cooking Time', 'Created At']
            # Custom column widths for better formatting
            col_widths = [80, 30, 40, 40]  # Title, Difficulty, Cooking Time, Created At
        elif report_type == 'favorites':
            cursor.execute('SELECT u.username, r.title as recipe_title, f.created_at FROM favorites f JOIN users u ON f.user_id = u.id JOIN recipes r ON f.recipe_id = r.id ORDER BY f.created_at DESC')
            data = cursor.fetchall()
            title = 'Favorites Report'
            headers = ['Username', 'Recipe Title', 'Created At']
        else:
            flash('Invalid report type', 'danger')
            return redirect(url_for('admin_dashboard'))

        cursor.close()
        connection.close()

        if not data:
            flash(f'No data to generate {report_type} report.', 'warning')
            return redirect(url_for('admin_dashboard'))

        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=16, style='B')

        # Title
        pdf.cell(200, 15, txt=title, ln=True, align='C')
        pdf.ln(10)

        # Set font for headers
        pdf.set_font("Arial", size=12, style='B')

        # Headers
        if 'col_widths' in locals():
            # Use custom widths for recipes report
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 12, header, border=1, align='C')
        else:
            # Uniform width for other reports
            col_width = 190 / len(headers)
            for header in headers:
                pdf.cell(col_width, 12, header, border=1, align='C')
        pdf.ln()

        # Set font for data
        pdf.set_font("Arial", size=10)

        # Data rows
        for row in data:
            cell_values = []
            cell_heights = []
            max_height = 10

            # First pass: calculate heights
            for i, header in enumerate(headers):
                key = header.lower().replace(' ', '_')
                if key == 'created_at':
                    value = str(row.get('created_at')) if row.get('created_at') else ''
                elif key == 'cooking_time':
                    value = str(row.get('cooking_time')) if row.get('cooking_time') else ''
                else:
                    value = str(row.get(key, ''))
                cell_values.append(value)
                if 'col_widths' in locals():
                    lines = pdf.multi_cell(col_widths[i], 10, value, border=0, align='L', split_only=True)
                else:
                    lines = pdf.multi_cell(col_width, 10, value, border=0, align='L', split_only=True)
                height = len(lines) * 10
                cell_heights.append(height)
                if height > max_height:
                    max_height = height

            # Second pass: draw cells
            start_y = pdf.get_y()
            for i, (value, height) in enumerate(zip(cell_values, cell_heights)):
                # Calculate line height to make all cells in row have same total height
                num_lines = height // 10 if height > 0 else 1
                line_height = max_height / num_lines if num_lines > 0 else max_height

                if 'col_widths' in locals():
                    x = pdf.l_margin + sum(col_widths[:i])
                    pdf.set_xy(x, start_y)
                    pdf.multi_cell(col_widths[i], line_height, value, border=1, align='L')
                    # Reset y position for next cell in row
                    pdf.set_xy(pdf.get_x(), start_y)
                else:
                    x = pdf.l_margin + i * col_width
                    pdf.set_xy(x, start_y)
                    pdf.multi_cell(col_width, line_height, value, border=1, align='L')
                    # Reset y position for next cell in row
                    pdf.set_xy(pdf.get_x(), start_y)

            # Move to next row
            pdf.set_xy(pdf.l_margin, start_y + max_height)

        pdf_output = pdf.output(dest='S')
        output = BytesIO(pdf_output.encode('latin-1'))
        output.seek(0)

        filename = f'{report_type}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    flash('Database error', 'danger')
    return redirect(url_for('admin_dashboard'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return "<h1>404 Not Found</h1><p>The requested URL was not found on the server.</p>", 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    # Rollback database session in case of error
    connection = get_db_connection()
    if connection:
        connection.rollback()
    return render_template('500.html'), 500

@app.route('/user/profile', methods=['GET', 'POST'])
def user_profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    if not connection:
        flash('Database connection failed', 'danger')
        return redirect(url_for('login'))

    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']

        image_url = request.form.get('current_image')
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                try:
                    file.save(filepath)
                    image_url = unique_filename
                except Exception as e:
                    app.logger.error(f"Error saving uploaded image: {e}")
                    return jsonify({'error': f'Error saving image: {str(e)}'}), 500
            else:
                return jsonify({'error': 'Invalid image file type'}), 400

        cursor.execute("UPDATE users SET username = %s, email = %s, image_url = %s WHERE id = %s",
                       (username, email, image_url, user_id))
        connection.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_profile'))

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    return render_template('user/profile.html', user=user)

@app.route('/user/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to change your password'}), 401

    user_id = session['user_id']
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_new_password = request.form['confirm_new_password']

    if new_password != confirm_new_password:
        flash('New passwords do not match', 'danger')
        return redirect(url_for('user_profile'))

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not check_password_hash(user['password_hash'], current_password):
        flash('Invalid current password', 'danger')
        return redirect(url_for('user_profile'))

    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
    cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hashed_password, user_id))
    connection.commit()
    cursor.close()
    connection.close()

    flash('Password updated successfully!', 'success')
    return redirect(url_for('user_profile'))

@app.route('/user/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to delete your account'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = connection.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    connection.commit()
    cursor.close()
    connection.close()

    session.clear()
    flash('Your account has been permanently deleted.', 'success')
    return redirect(url_for('index'))

@app.route('/verify_2fa_login', methods=['GET', 'POST'])
def verify_2fa_login():
    if 'temp_user_id' not in session:
        return jsonify({'error': 'Unauthorized access'}), 401

    user_id = session['temp_user_id']
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user or not user['is_2fa_enabled'] or not user['otp_secret']:
        return jsonify({'error': '2FA not enabled for this account'}), 400

    if request.method == 'POST':
        otp = request.form['otp']
        totp = pyotp.TOTP(user['otp_secret'])

        if totp.verify(otp):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session.permanent = True
            session.pop('temp_user_id', None)
            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid 2FA code', 'danger')

    cursor.close()
    connection.close()
    return render_template('verify_2fa_login.html')

@app.route('/user/enable_2fa')
def enable_2fa():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to enable 2FA'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if user['is_2fa_enabled']:
        flash('2FA is already enabled', 'info')
        return redirect(url_for('user_profile'))

    otp_secret = pyotp.random_base32()
    cursor.execute("UPDATE users SET otp_secret = %s WHERE id = %s", (otp_secret, user_id))
    connection.commit()

    return render_template('user/enable_2fa.html', otp_secret=otp_secret)

@app.route('/user/disable_2fa')
def disable_2fa():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = connection.cursor()
    cursor.execute("UPDATE users SET is_2fa_enabled = FALSE, otp_secret = NULL WHERE id = %s", (user_id,))
    connection.commit()
    cursor.close()
    connection.close()

    flash('2FA has been disabled', 'success')
    return redirect(url_for('user_profile'))

@app.route('/user/verify_2fa', methods=['POST'])
def verify_2fa():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    otp = request.form['otp']

    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    totp = pyotp.TOTP(user['otp_secret'])
    if totp.verify(otp):
        cursor.execute("UPDATE users SET is_2fa_enabled = TRUE WHERE id = %s", (user_id,))
        connection.commit()
        flash('2FA has been enabled successfully!', 'success')
    else:
        flash('Invalid authentication code', 'danger')

    cursor.close()
    connection.close()
    return redirect(url_for('user_profile'))

@app.route('/api/notifications', methods=['GET', 'POST', 'DELETE'])
def get_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    notifications = []
    if connection:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            notification_id = request.json.get('notification_id')
            if notification_id:
                cursor.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s", (notification_id, user_id))
                connection.commit()
                return jsonify({'status': 'success'})
        elif request.method == 'DELETE':
            cursor.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
            connection.commit()
            return jsonify({'status': 'success'})

        cursor.execute("SELECT * FROM notifications WHERE user_id = %s AND is_read = FALSE ORDER BY created_at DESC", (user_id,))
        notifications = cursor.fetchall()
        cursor.close()
        connection.close()

    return jsonify(notifications)

@app.route('/diet_planner', methods=['GET', 'POST'])
def diet_planner():
    if 'user_id' not in session:
        flash('Please log in to use the diet planner', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    diet_plans = []
    if connection:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            goal = request.form.get('goal')
            if goal == 'custom':
                goal = request.form.get('customGoal')

            if not goal:
                flash('Please select a valid goal.', 'danger')
                return render_template('diet_planner.html', form_data=request.form)
            
            try:
                goal_amount = float(goal)
            except ValueError:
                flash('Invalid goal amount.', 'danger')
                return render_template('diet_planner.html', form_data=request.form)

            goal_type = "gain" if goal_amount > 0 else "lose"
            goal_abs = abs(goal_amount)
                
            days = int(request.form.get('days', 7))
            allergies = request.form.get('allergies', '')

            # Store allergies in the database
            user_id = session['user_id']
            connection = get_db_connection()
            if connection:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM user_allergies WHERE user_id = %s", (user_id,))
                if allergies:
                    for allergy in allergies.split(','):
                        cursor.execute("INSERT INTO user_allergies (user_id, allergy) VALUES (%s, %s)", (user_id, allergy.strip()))
                connection.commit()
                cursor.close()
                connection.close()

            # Generate diet plan using Gemini
            prompt = f"""Create a {days}-day diet plan for weight {goal_type} of {goal_abs} kg. Allergies: {allergies}.

Requirements:
- EXACTLY {days} days (1 to {days})
- Each day: 3 meals (Breakfast, Lunch, Dinner)
- For {goal_type}: {"calorie-dense foods, larger portions" if goal_type == "gain" else "calorie-controlled portions"}
- Avoid: {allergies}

Return JSON: {{"plan_name": "Weight {goal_type.capitalize()} Plan", "meals": [array of {days * 3} meal objects with day, meal_type, meal_name, description, ingredients array, prep_time]}}"""
            
            raw_response = call_gemini_api(prompt)
            if raw_response.startswith("Sorry"):
                flash(raw_response, 'danger')
                return render_template('diet_planner.html', form_data=request.form)

            meal_plan_json = clean_json_response(raw_response)

            if not meal_plan_json:
                flash("Sorry, the AI returned an invalid format. Please try again.", 'danger')
                return render_template('diet_planner.html', form_data=request.form)

            try:
                meal_plan = json.loads(meal_plan_json)
                # Add created_at to the meal_plan for consistency with database plans
                meal_plan['created_at'] = datetime.now()
                meal_plan['goal'] = f"{goal_type.capitalize()} {goal_abs} kg" # Make goal more descriptive
                meal_plan['generated'] = True  # Mark as generated plan
                return render_template('user/my_diet_plan.html', diet_plans=[meal_plan])
            except (json.JSONDecodeError, Error) as e:
                flash(f"Error processing diet plan: {str(e)}", 'danger')
                return render_template('diet_planner.html', form_data=request.form)

        return render_template('diet_planner.html')

@app.route('/my_diet_plan', methods=['GET', 'POST'])
def my_diet_plan():
    if 'user_id' not in session or session.get('is_admin'):
        flash('Please log in as a user to access this page', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    diet_plans = []
    if connection:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            if 'plan_id' in request.form and 'delete' not in request.form and 'export' not in request.form and 'toggle_active' not in request.form:
                plan_id = request.form['plan_id']
                cursor.execute("UPDATE diet_plans SET is_active = FALSE WHERE user_id = %s", (user_id,))
                cursor.execute("UPDATE diet_plans SET is_active = TRUE WHERE id = %s AND user_id = %s", (plan_id, user_id))
                connection.commit()
                flash('Active diet plan updated successfully!', 'success')
                return redirect(url_for('my_diet_plan'))

            elif 'plan_id' in request.form and 'toggle_active' in request.form:
                plan_id = request.form['plan_id']
                # Check current status
                cursor.execute("SELECT is_active FROM diet_plans WHERE id = %s AND user_id = %s", (plan_id, user_id))
                current_status = cursor.fetchone()
                if current_status:
                    new_status = not current_status['is_active']
                    if new_status:
                        # Deactivate all other plans if activating this one
                        cursor.execute("UPDATE diet_plans SET is_active = FALSE WHERE user_id = %s", (user_id,))
                    cursor.execute("UPDATE diet_plans SET is_active = %s WHERE id = %s AND user_id = %s", (new_status, plan_id, user_id))
                    connection.commit()
                    # Invalidate user dashboard cache
                    cache_key = f"user_dashboard_{user_id}"
                    with db_cache_lock:
                        db_cache.pop(cache_key, None)
                    status_msg = 'activated' if new_status else 'deactivated'
                    flash(f'Diet plan {status_msg} successfully!', 'success')
                return redirect(url_for('my_diet_plan'))

            elif 'plan_id' in request.form and 'delete' in request.form:
                plan_id = request.form['plan_id']
                cursor.execute("DELETE FROM diet_plans WHERE id = %s AND user_id = %s", (plan_id, user_id))
                connection.commit()
                flash('Diet plan deleted successfully!', 'success')
                return redirect(url_for('my_diet_plan'))

            elif 'plan_id' in request.form and 'export' in request.form:
                plan_id = request.form['plan_id']
                cursor.execute("SELECT * FROM diet_plans WHERE id = %s AND user_id = %s", (plan_id, user_id))
                plan = cursor.fetchone()

                if not plan:
                    flash('Diet plan not found.', 'danger')
                    return redirect(url_for('my_diet_plan'))

                cursor.execute("SELECT * FROM diet_plan_meals WHERE diet_plan_id = %s", (plan['id'],))
                meals_raw = cursor.fetchall()

                # Group meals by day
                meals_by_day = {}
                for meal in meals_raw:
                    day = meal['day']
                    if day not in meals_by_day:
                        meals_by_day[day] = []
                    meals_by_day[day].append(meal)

                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)

                # Title
                pdf.set_font("Arial", size=24, style='B')
                pdf.cell(0, 10, txt=plan['plan_name'], ln=True, align='C')
                pdf.ln(10)

                # Goal
                pdf.set_font("Arial", size=14)
                pdf.cell(0, 10, txt=f"Goal: {plan['goal']}", ln=True, align='L')
                pdf.ln(5)

                # Table Headers
                col_widths = [20, 30, 50, 90]
                headers = ["Day", "Meal", "Name", "Ingredients"]

                pdf.set_font("Arial", size=10, style='B')
                for i, header in enumerate(headers):
                    pdf.cell(col_widths[i], 10, header, border=1, align='C')
                pdf.ln()

                pdf.set_font("Arial", size=10)
                line_height_for_calc = 5

                for day_num in sorted(meals_by_day.keys()):
                    for meal in meals_by_day[day_num]:
                        day_content = str(meal['day'])
                        meal_type_content = meal['meal_type']
                        meal_name_content = meal['meal_name']
                        ingredients_content = ""
                        if meal['ingredients']:
                            ingredients_list = json.loads(meal['ingredients']) if isinstance(meal['ingredients'], str) else meal['ingredients']
                            ingredients_content = "\n".join([f"- {ing}" for ing in ingredients_list])

                        temp_pdf_calc = FPDF()
                        temp_pdf_calc.add_page()
                        temp_pdf_calc.set_font("Arial", size=10)
                        h_day = temp_pdf_calc.get_string_width(day_content) / col_widths[0] * line_height_for_calc or line_height_for_calc
                        h_meal_type = temp_pdf_calc.get_string_width(meal_type_content) / col_widths[1] * line_height_for_calc or line_height_for_calc
                        h_meal_name = temp_pdf_calc.get_string_width(meal_name_content) / col_widths[2] * line_height_for_calc or line_height_for_calc
                        num_ingredient_lines = ingredients_content.count('\n') + 1 if ingredients_content else 1
                        h_ingredients = num_ingredient_lines * line_height_for_calc or line_height_for_calc

                        current_max_height = max(h_day, h_meal_type, h_meal_name, h_ingredients) + 2
                        if current_max_height < 10:
                            current_max_height = 10

                        start_x = pdf.get_x()
                        start_y = pdf.get_y()

                        pdf.multi_cell(col_widths[0], line_height_for_calc, day_content, border=1, align='C')
                        pdf.set_xy(start_x + col_widths[0], start_y)
                        pdf.multi_cell(col_widths[1], line_height_for_calc, meal_type_content, border=1, align='C')
                        pdf.set_xy(start_x + col_widths[0] + col_widths[1], start_y)
                        pdf.multi_cell(col_widths[2], line_height_for_calc, meal_name_content, border=1, align='L')
                        pdf.set_xy(start_x + col_widths[0] + col_widths[1] + col_widths[2], start_y)
                        pdf.multi_cell(col_widths[3], line_height_for_calc, ingredients_content, border=1, align='L')
                        pdf.set_xy(start_x, start_y + current_max_height)

                pdf_output = pdf.output(dest='S').encode('latin-1')
                output = BytesIO(pdf_output)
                output.seek(0)
                filename = f'{plan["plan_name"].replace(" ", "_")}_Diet_Plan.pdf'

                return send_file(output, as_attachment=True, download_name=filename, mimetype='application/pdf')

            else:
                # 🟢 Create a new diet plan (saved as INACTIVE)
                plan_name = request.form['plan_name']
                goal = request.form['goal']
                meals = json.loads(request.form['meals'])

                # No deactivation of existing plans
                # cursor.execute("UPDATE diet_plans SET is_active = FALSE WHERE user_id = %s", (user_id,))

                # Save new plan as inactive
                cursor.execute(
                    "INSERT INTO diet_plans (user_id, plan_name, goal, is_active) VALUES (%s, %s, %s, %s)",
                    (user_id, plan_name, goal, False)
                )
                diet_plan_id = cursor.lastrowid

                for meal in meals:
                    cursor.execute(
                        "INSERT INTO diet_plan_meals (diet_plan_id, day, meal_type, meal_name, description, ingredients, prep_time) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            diet_plan_id,
                            meal['day'],
                            meal['meal_type'],
                            meal['meal_name'],
                            meal['description'],
                            json.dumps(meal['ingredients']),
                            meal['prep_time']
                        )
                    )

                connection.commit()
                flash('Diet plan saved successfully (inactive by default).', 'success')
                return redirect(url_for('my_diet_plan'))

        # Fetch diet plans
        cursor.execute("SELECT * FROM diet_plans WHERE user_id = %s ORDER BY is_active DESC, created_at DESC", (user_id,))
        diet_plans = cursor.fetchall()

        for plan in diet_plans:
            cursor.execute("SELECT * FROM diet_plan_meals WHERE diet_plan_id = %s", (plan['id'],))
            plan['meals'] = cursor.fetchall()

            for meal in plan['meals']:
                if isinstance(meal.get('ingredients'), str):
                    try:
                        meal['ingredients'] = json.loads(meal['ingredients'])
                    except json.JSONDecodeError:
                        meal['ingredients'] = [meal['ingredients']]

            # Weekly adherence
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)

            cursor.execute(
                "SELECT COUNT(*) as total_meals FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id IN "
                "(SELECT id FROM diet_plan_meals WHERE diet_plan_id = %s) AND date BETWEEN %s AND %s",
                (user_id, plan['id'], start_of_week, end_of_week)
            )
            total_meals = cursor.fetchone()['total_meals']

            cursor.execute(
                "SELECT COUNT(*) as completed_meals FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id IN "
                "(SELECT id FROM diet_plan_meals WHERE diet_plan_id = %s) AND status = 'Completed' AND date BETWEEN %s AND %s",
                (user_id, plan['id'], start_of_week, end_of_week)
            )
            completed_meals = cursor.fetchone()['completed_meals']

            plan['adherence'] = int((completed_meals / total_meals) * 100) if total_meals > 0 else 0

            # Streak calculation
            cursor.execute(
                "SELECT date FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id IN "
                "(SELECT id FROM diet_plan_meals WHERE diet_plan_id = %s) AND status = 'Completed' ORDER BY date DESC",
                (user_id, plan['id'])
            )
            completed_dates = [row['date'] for row in cursor.fetchall()]

            streak = 0
            if completed_dates:
                streak = 1
                for i in range(len(completed_dates) - 1):
                    if (completed_dates[i] - completed_dates[i + 1]).days == 1:
                        streak += 1
                    else:
                        break
            plan['streak'] = streak

            cursor.execute(
                "SELECT COUNT(*) as total_completed FROM meal_tracking mt "
                "JOIN diet_plan_meals dpm ON mt.diet_plan_meal_id = dpm.id "
                "WHERE mt.user_id = %s AND dpm.diet_plan_id = %s AND mt.status = 'Completed'",
                (user_id, plan['id'])
            )
            plan['total_completed_meals'] = cursor.fetchone()['total_completed']

            cursor.execute(
                "SELECT COUNT(*) as total_skipped FROM meal_tracking mt "
                "JOIN diet_plan_meals dpm ON mt.diet_plan_meal_id = dpm.id "
                "WHERE mt.user_id = %s AND dpm.diet_plan_id = %s AND mt.status = 'Skipped'",
                (user_id, plan['id'])
            )
            plan['total_skipped_meals'] = cursor.fetchone()['total_skipped']

        cursor.close()
        connection.close()

    return render_template('user/my_diet_plan.html', diet_plans=diet_plans)


@app.route('/track_weight', methods=['GET', 'POST'])
def track_weight():
    if 'user_id' not in session:
        flash('Please log in to track your weight', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    weight_history = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM weight_tracking WHERE user_id = %s ORDER BY date DESC", (user_id,))
        weight_history = cursor.fetchall()
        cursor.close()
        connection.close()

    if request.method == 'POST':
        weight = request.form['weight']
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO weight_tracking (user_id, weight, date) VALUES (%s, %s, %s)", (user_id, weight, datetime.now().date()))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Weight logged successfully!', 'success')
            return redirect(url_for('track_weight'))

    return render_template('track_weight.html', weight_history=weight_history)

@app.route('/save_diet_plan', methods=['POST'])
def save_diet_plan():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to save diet plans'}), 401

    data = request.json
    plan_name = data.get('plan_name')
    goal = data.get('goal')
    meals = data.get('meals')

    if not plan_name or not goal or not meals:
        return jsonify({'error': 'Missing data'}), 400

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO diet_plans (user_id, plan_name, goal) VALUES (%s, %s, %s)", (user_id, plan_name, goal))
        diet_plan_id = cursor.lastrowid

        for meal in meals:
            cursor.execute("INSERT INTO diet_plan_meals (diet_plan_id, day, meal_type, meal_name, description, ingredients, prep_time) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                           (diet_plan_id, meal['day'], meal['meal_type'], meal['meal_name'], meal['description'], json.dumps(meal['ingredients']), meal['prep_time']))

        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'status': 'success', 'message': 'Diet plan saved successfully!'})

    return jsonify({'error': 'Database error'}), 500

@app.route('/api/track_meal', methods=['POST'])
def track_meal():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    meal_id = data.get('meal_id')
    status = data.get('status')

    if not meal_id:
        return jsonify({'error': 'Missing meal_id'}), 400

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        if status in ['Completed', 'Skipped']:
            cursor.execute("INSERT INTO meal_tracking (user_id, diet_plan_meal_id, status, date) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE status = %s", 
                           (user_id, meal_id, status, datetime.now().date(), status))
        elif status is None: # If status is None, it means the meal is unmarked
            cursor.execute("DELETE FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id = %s AND date = %s",
                           (user_id, meal_id, datetime.now().date()))
        else:
            return jsonify({'error': 'Invalid status provided'}), 400

        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'status': 'success'})

    return jsonify({'error': 'Database error'}), 500

@app.route('/api/track_meals_batch', methods=['POST'])
def track_meals_batch():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    updates = data.get('updates')

    if not updates or not isinstance(updates, list):
        return jsonify({'error': 'Missing or invalid updates data'}), 400

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            for update in updates:
                meal_id = update.get('meal_id')
                status = update.get('status')

                if not meal_id:
                    # Skip invalid updates, or return an error for the whole batch
                    continue 

                if status in ['Completed', 'Skipped']:
                    cursor.execute("INSERT INTO meal_tracking (user_id, diet_plan_meal_id, status, date) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE status = %s", 
                                   (user_id, meal_id, status, datetime.now().date(), status))
                elif status is None: # If status is None, it means the meal is unmarked
                    cursor.execute("DELETE FROM meal_tracking WHERE user_id = %s AND diet_plan_meal_id = %s AND date = %s",
                                   (user_id, meal_id, datetime.now().date()))
                # else: Invalid status, skip or log

            connection.commit()
            return jsonify({'status': 'success', 'message': 'Batch update successful'})
        except Error as e:
            connection.rollback()
            app.logger.error(f"Database error during batch meal tracking: {e}")
            return jsonify({'error': 'Database error during batch update'}), 500
        finally:
            cursor.close()
            connection.close()
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/save_nutrition_analysis', methods=['POST'])
def save_nutrition_analysis():
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to save nutrition analyses'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    analysis_name = data.get('analysis_name')
    analysis_data = data.get('analysis_data')

    if not analysis_name or not analysis_data:
        return jsonify({'error': 'Missing analysis name or data'}), 400

    try:
        analysis_json = json.loads(analysis_data)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid analysis data format'}), 400

    if not isinstance(analysis_json, dict) or 'ingredients' not in analysis_json or 'analysis' not in analysis_json:
        return jsonify({'error': 'Invalid analysis data structure'}), 400

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        # Check if this analysis already exists for the user
        cursor.execute('SELECT id FROM nutrition_analysis WHERE user_id = %s AND name = %s',
                       (user_id, analysis_name))
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            connection.close()
            return jsonify({'error': 'A nutrition analysis with this name already exists'}), 400

        cursor.execute('INSERT INTO nutrition_analysis (user_id, name, ingredients, analysis) VALUES (%s, %s, %s, %s)',
                       (user_id, analysis_name, json.dumps(analysis_json['ingredients']), json.dumps(analysis_json['analysis'])))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'status': 'success', 'message': 'Nutrition analysis saved successfully!'})

    return jsonify({'error': 'Database error'}), 500

@app.route('/delete_nutrition_analysis/<int:analysis_id>', methods=['POST'])
def delete_nutrition_analysis(analysis_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to delete nutrition analyses'}), 401

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM nutrition_analysis WHERE id = %s AND user_id = %s', (analysis_id, user_id))
        deleted_rows = cursor.rowcount
        connection.commit()
        cursor.close()
        connection.close()

        if deleted_rows > 0:
            return jsonify({'status': 'success', 'message': 'Nutrition analysis deleted successfully!'})
        else:
            return jsonify({'error': 'Nutrition analysis not found or you do not have permission to delete it'}), 404

    return jsonify({'error': 'Database error'}), 500

@app.route('/nutrition_analysis_detail/<int:analysis_id>')
def nutrition_analysis_detail(analysis_id):
    if 'user_id' not in session:
        flash('Please log in to view this page', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM nutrition_analysis WHERE id = %s AND user_id = %s', (analysis_id, user_id))
        analysis = cursor.fetchone()
        cursor.close()
        connection.close()

        if analysis:
            return render_template('nutrition_analysis_detail.html', analysis=analysis)
        else:
            flash('Analysis not found', 'danger')
            return redirect(url_for('nutrition_helper'))

    return redirect(url_for('nutrition_helper'))

@app.route('/api/config')
def get_api_config():
    return jsonify({
        'baseUrl': app.config['GEMINI_BASE_URL'],
        'version': app.config['GEMINI_VERSION'],
        'textModel': app.config['GEMINI_TEXT_MODEL']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))
    app.run(host='0.0.0.0', port=port)
    app.run(debug=True)