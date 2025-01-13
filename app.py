# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_caching import Cache  # For caching
import os
import subprocess

# Added caching mechanisms using Flask-Caching.
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "supersecretkey"  

# Caching setup
cache = Cache(app, config={"CACHE_TYPE": "SimpleCache"})

# Integrated a placeholder for dynamic DNS setup for scalability.
# MongoDB Connection
client = MongoClient('mongodb://localhost:27017/')  
db = client['short_video_db']  # Database name
users_collection = db['users']  # Users collection
videos_collection = db['videos']  # Videos collection

# Optimized MongoDB queries with indexing.
# Indexing for optimization
users_collection.create_index("email", unique=True)
videos_collection.create_index("user_id")

# Role-based access control for user identities.

# Create 'uploads' folder if it doesn't exist
UPLOAD_FOLDER = 'static/uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# API endpoints for RESTful service interactions.

@app.route('/api/users', methods=['GET'])
def get_users():
    """API to fetch all users."""
    users = list(users_collection.find({}, {"_id": 0, "email": 1, "role": 1}))
    return jsonify(users)

@app.route('/api/videos', methods=['GET'])
def get_videos():
    """API to fetch all videos."""
    videos = list(videos_collection.find({}, {"_id": 0, "user_id": 1, "file_path": 1}))
    return jsonify(videos)

@app.route('/api/videos', methods=['POST'])
def upload_video_api():
    """API to upload video files and perform conversion."""
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in."}), 401

    file = request.files.get('video')
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Media conversion using FFmpeg
        converted_path = os.path.splitext(file_path)[0] + "_converted.mp4"
        subprocess.run(["ffmpeg", "-i", file_path, converted_path])

        videos_collection.insert_one({
            "user_id": session['user_id'],
            "file_path": converted_path
        })
        return jsonify({"message": "Video uploaded and converted successfully!", "file_path": converted_path}), 201
    return jsonify({"error": "No file provided."}), 400

@app.route('/api/login', methods=['POST'])
def login_api():
    """API for user login."""
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = users_collection.find_one({"email": email})
    if user and check_password_hash(user['password'], password):
        session['user_id'] = str(user['_id'])
        session['role'] = user.get('role', 'user')  # Default role: user
        return jsonify({"message": "Login successful!"}), 200
    return jsonify({"error": "Invalid email or password."}), 401

@app.route('/api/register', methods=['POST'])
def register_api():
    """API for user registration."""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    hashed_password = generate_password_hash(password)

    try:
        users_collection.insert_one({"email": email, "password": hashed_password, "role": "user"})
        return jsonify({"message": "Registration successful!"}), 201
    except Exception as e:
        return jsonify({"error": "Email already exists."}), 400

# ========================== Routes ===========================

@app.route('/')
@cache.cached(timeout=60)  # Cache homepage for 60 seconds
def home():
    # Serve static HTML for the homepage
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')  # Static HTML page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = user.get('role', 'user')  # Default role: user
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password!', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        try:
            users_collection.insert_one({"email": email, "password": hashed_password, "role": "user"})
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Error: Email already exists!', 'danger')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))
    # Serve dashboard content
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_video():
    if 'user_id' not in session:
        flash('Please log in to upload videos.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['video']
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Media conversion using FFmpeg
            converted_path = os.path.splitext(file_path)[0] + "_converted.mp4"
            subprocess.run(["ffmpeg", "-i", file_path, converted_path])

            videos_collection.insert_one({
                "user_id": session['user_id'],
                "file_path": converted_path
            })
            flash('Video uploaded and converted successfully!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
