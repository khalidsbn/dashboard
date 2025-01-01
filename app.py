from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "supersecretkey"  # Replace this with your own secret key

# MongoDB Connection
client = MongoClient('mongodb://localhost:27017/')  # Use your MongoDB URL
db = client['video_db']  # Database name
users_collection = db['users']  # Users collection
videos_collection = db['videos']  # Videos collection

# Create 'uploads' folder if it doesn't exist
UPLOAD_FOLDER = 'static/uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ========================== Routes ===========================

# Route: Home
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Route: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        firstname = request.form['firstname']
        secondname = request.form['secondname']
        age = request.form['age']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validate passwords
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))

        # Check if email already exists
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('Email already registered!', 'error')
            return redirect(url_for('register'))

        # Hash the password and save to MongoDB
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            'firstname': firstname,
            'secondname': secondname,
            'age': int(age),  # Store age as an integer
            'username': username,
            'email': email,
            'password': hashed_password
        })

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if user exists
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Route: Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('login'))
    
    # Fetch videos uploaded by the logged-in user
    user_id = session.get('user_id')  # Get the logged-in user's ID from the session
    videos = videos_collection.find({'uploaded_by': user_id})  # Retrieve only this user's videos
    
    return render_template('index.html', username=session.get('username'), videos=videos)

# Route: Upload Video
@app.route('/upload', methods=['GET', 'POST'])
def upload_video():
    # Check if the user is logged in
    if 'user_id' not in session:  # Assuming user_id is stored in the session during login
        flash('Please log in to upload videos.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        video_title = request.form.get('title')
        hashtags = request.form.get('hashtags')
        category = request.form.get('category')
        description = request.form.get('description')
        file = request.files.get('file')

        # Validate the file
        if file and file.filename:
            # Save the file to the uploads folder
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            try:
                file.save(file_path)
            except Exception as e:
                flash(f"Error saving file: {str(e)}", 'error')
                return redirect(url_for('upload_video'))

            # Save video details to MongoDB
            video_data = {
                'title': video_title,
                'hashtags': hashtags,
                'category': category,
                'description': description,
                'file_name': file.filename,
                'uploaded_by': session['user_id']  # Link video to the logged-in user
            }
            try:
                videos_collection.insert_one(video_data)
                flash('Video uploaded successfully!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f"Error saving video details: {str(e)}", 'error')
                return redirect(url_for('upload_video'))
        else:
            flash('Please upload a valid file.', 'error')
            return redirect(url_for('upload_video'))

    return render_template('upload.html')


@app.route('/settings')
def settings():
    if 'user_id' not in session:
        flash('Please log in to access your settings.', 'error')
        return redirect(url_for('login'))
    
    # Fetch user details from the database
    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})  # Assuming you're using MongoDB
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))
    
    # Pass user details to the template
    return render_template(
        'settings.html',
        firstname=user.get('firstname', ''),
        secondname=user.get('secondname', ''),
        age=user.get('age', ''),
        username=user.get('username', ''),
        email=user.get('email', '')
    )

# ========================== Main ===========================
if __name__ == '__main__':
    app.run(debug=True)
