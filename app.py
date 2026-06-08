import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from models import db, Car, AdminUser

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'default-fallback-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///fallback.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static' , 'uploads') 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg' , 'webp'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

##like @GetMapping in Spring Boot
@app.route('/')
def home():
    garage_name = "Luca's Garage"
    return render_template('index.html', name="Luca's Garage")

@app.route('/cars')
def cars():
    all_cars = Car.query.all()
    return render_template('cars.html', cars=all_cars)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Look up the admin in MariaDB
        user = AdminUser.query.filter_by(username=username).first()
        
        # Verify user exists and the hashed password matches perfectly
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
            
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin_dashboard():
    all_cars = Car.query.all()
    return render_template('admin.html', cars=all_cars)

@app.route('/admin/add', methods=['POST'])
@login_required
def add_car():
    make_model = request.form['make_model']
    year = request.form['year']
    price = request.form['price']
    TransmissionType = request.form['TransmissionType']
    fuel_type = request.form['fuel_type']
    image = request.files['image']

    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_car = Car(make_model=make_model, year=year, price=price, TransmissionType=TransmissionType, fuel_type=fuel_type, image_filename=filename)
        db.session.add(new_car)
        db.session.commit()
        flash('Car added successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid image file.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
@app.route('/admin/delete/<int:id>', methods=['POST'])
@login_required
def delete_car(id):
    car_to_delete = Car.query.get_or_404(id)
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], car_to_delete.image_filename))
    except FileNotFoundError:
        pass
    db.session.delete(car_to_delete)
    db.session.commit()
    flash('Car deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

with app.app_context():
    db.create_all()
    
    env_admin_username = os.getenv('ADMIN_USER')
    env_admin_password = os.getenv('ADMIN_PASSWORD')
    
    # Strict Production Check: If either variable is completely missing, 
    if not env_admin_username or not env_admin_password:
        raise ValueError(
            "CRITICAL CONFIGURATION ERROR: 'ADMIN_USER' and 'ADMIN_PASSWORD' "
            "must be explicitly set in your environment variables. App execution halted."
        )
        
    # If the check passes, proceed to seed securely
    if not AdminUser.query.filter_by(username=env_admin_username).first():
        secure_hash = generate_password_hash(env_admin_password)
        seed_admin = AdminUser(username=env_admin_username, password_hash=secure_hash)
        db.session.add(seed_admin)
        db.session.commit()
        print(f"Database successfully initialized with account: '{env_admin_username}'")



if __name__ == '__main__':
    app.run(debug=True)