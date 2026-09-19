import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

from models import db, Car, AdminUser, Booking
from services.whatsapp import (
    send_whatsapp_booking_alert,
    generate_customer_whatsapp_url,
    generate_luca_reply_whatsapp_url,
    GARAGE_MOBILE
)
from services.ai_assistant import generate_ai_response, GARAGE_INFO

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'default-fallback-dev-key-lucas-garage')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///garage.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Context processor for templates to always have garage info & direct WhatsApp
@app.context_processor
def inject_garage_data():
    return {
        "garage_info": GARAGE_INFO,
        "garage_mobile": GARAGE_MOBILE,
        "default_whatsapp_url": generate_customer_whatsapp_url()
    }

# ----------------- PUBLIC ROUTES ----------------- #

@app.route('/')
def home():
    featured_cars = Car.query.filter(Car.status != 'Sold').order_by(Car.created_at.desc()).limit(3).all()
    return render_template('index.html', cars=featured_cars)

@app.route('/cars')
def cars():
    all_cars = Car.query.order_by(Car.status == 'Sold', Car.created_at.desc()).all()
    return render_template('cars.html', cars=all_cars)

@app.route('/car/<int:id>')
def car_detail(id):
    car = Car.query.get_or_404(id)
    whatsapp_url = generate_customer_whatsapp_url(car_name=f"{car.year} {car.make_model}", message_type="inquiry")
    return render_template('car_detail.html', car=car, whatsapp_url=whatsapp_url)

# ----------------- API ENDPOINTS (CHAT & BOOKINGS) ----------------- #

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    reply = generate_ai_response(user_message)
    return jsonify({"reply": reply})

@app.route('/api/book-viewing', methods=['POST'])
def book_viewing_api():
    data = request.get_json() if request.is_json else request.form.to_dict()

    car_id = data.get('car_id')
    customer_name = data.get('customer_name', '').strip()
    customer_phone = data.get('customer_phone', '').strip()
    customer_email = data.get('customer_email', '').strip()
    booking_date = data.get('booking_date', '').strip() # YYYY-MM-DD
    booking_time = data.get('booking_time', '').strip() # HH:MM
    notes = data.get('notes', '').strip()

    if not (car_id and customer_name and customer_phone and booking_date and booking_time):
        return jsonify({"success": False, "message": "Please fill in all required fields (Name, Phone, Date, Time)."}), 400

    car = Car.query.get(int(car_id))
    if not car:
        return jsonify({"success": False, "message": "Vehicle not found."}), 404

    # Validate garage hours:
    # Mon-Fri: 9:00 - 18:00; Sat: 13:00 - 18:00; Sun: Closed
    try:
        dt = datetime.strptime(booking_date, "%Y-%m-%d")
        weekday = dt.weekday() # 0 = Monday, 5 = Saturday, 6 = Sunday
        hour = int(booking_time.split(":")[0])
        minute = int(booking_time.split(":")[1])
        time_decimal = hour + (minute / 60.0)

        if weekday == 6:
            return jsonify({"success": False, "message": "The garage is closed on Sundays. Please choose Monday through Saturday."}), 400
        elif weekday == 5 and (time_decimal < 13.0 or time_decimal > 17.5):
            return jsonify({"success": False, "message": "Saturday opening hours are 1:00 PM – 6:00 PM. Please choose a slot between 13:00 and 17:30."}), 400
        elif weekday < 5 and (time_decimal < 9.0 or time_decimal > 17.5):
            return jsonify({"success": False, "message": "Weekday opening hours are 9:00 AM – 6:00 PM. Please choose a slot between 09:00 and 17:30."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Invalid date or time format: {e}"}), 400

    # Prevent double-booking for the exact same car, date, and time
    existing = Booking.query.filter_by(
        car_id=car.id,
        booking_date=booking_date,
        booking_time=booking_time,
        status="Confirmed"
    ).first()
    if existing:
        return jsonify({"success": False, "message": "This time slot is already reserved for this vehicle. Please choose another slot."}), 400

    booking = Booking(
        car_id=car.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        booking_date=booking_date,
        booking_time=booking_time,
        notes=notes,
        status="Confirmed"
    )
    db.session.add(booking)
    db.session.commit()

    # Dispatch WhatsApp alert to Luca
    send_whatsapp_booking_alert(booking, car)

    # Customer 1-click confirmation link
    customer_confirm_url = generate_customer_whatsapp_url(
        car_name=f"{car.year} {car.make_model}",
        message_type="viewing"
    )

    return jsonify({
        "success": True,
        "message": f"Viewing confirmed for {booking_date} at {booking_time}! Luca has received your booking on WhatsApp.",
        "customer_whatsapp_url": customer_confirm_url
    })

# ----------------- ADMIN ROUTES ----------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
            
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin_dashboard():
    all_cars = Car.query.order_by(Car.created_at.desc()).all()
    upcoming_bookings = Booking.query.order_by(Booking.booking_date.asc(), Booking.booking_time.asc()).all()

    # Generate 1-tap WhatsApp reply link for each booking
    booking_items = []
    for b in upcoming_bookings:
        reply_url = generate_luca_reply_whatsapp_url(
            customer_phone=b.customer_phone,
            car_name=b.car.make_model if b.car else "the vehicle",
            booking_date=b.booking_date,
            booking_time=b.booking_time
        )
        booking_items.append({
            "booking": b,
            "reply_url": reply_url
        })

    return render_template('admin.html', cars=all_cars, bookings=booking_items)

@app.route('/admin/add', methods=['POST'])
@login_required
def add_car():
    make_model = request.form.get('make_model')
    year = int(request.form.get('year', 2018))
    price = int(request.form.get('price', 0))
    TransmissionType = request.form.get('TransmissionType', 'Manual')
    fuel_type = request.form.get('fuel_type', 'Petrol')
    
    # Enhanced fields
    mileage = int(request.form.get('mileage') or 0)
    ulez_compliant = True if request.form.get('ulez_compliant') == 'on' else False
    mot_expiry = request.form.get('mot_expiry', '12 Months MOT')
    copart_category = request.form.get('copart_category', 'Clean / Unrecorded')
    repair_notes = request.form.get('repair_notes', '')
    features = request.form.get('features', '')

    image = request.files.get('image')

    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        # Avoid filename collisions
        timestamp_prefix = datetime.now().strftime("%Y%m%d%H%M%S_")
        saved_filename = timestamp_prefix + filename
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))
        
        new_car = Car(
            make_model=make_model,
            year=year,
            price=price,
            TransmissionType=TransmissionType,
            fuel_type=fuel_type,
            image_filename=saved_filename,
            mileage=mileage,
            ulez_compliant=ulez_compliant,
            mot_expiry=mot_expiry,
            copart_category=copart_category,
            repair_notes=repair_notes,
            features=features,
            status='Available'
        )
        db.session.add(new_car)
        db.session.commit()
        flash('Vehicle listed successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid image file. Please upload JPG, PNG, or WebP.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/status/<int:id>/<string:new_status>', methods=['POST'])
@login_required
def update_status(id, new_status):
    car = Car.query.get_or_404(id)
    if new_status in ['Available', 'Reserved', 'Sold']:
        car.status = new_status
        db.session.commit()
        flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/booking/cancel/<int:id>', methods=['POST'])
@login_required
def cancel_booking(id):
    booking = Booking.query.get_or_404(id)
    booking.status = 'Cancelled'
    db.session.commit()
    flash('Viewing appointment marked as cancelled.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/marketplace-text/<int:id>')
@login_required
def marketplace_text(id):
    car = Car.query.get_or_404(id)
    ulez_text = "YES - ULEZ EXEMPT (Euro 6)" if car.ulez_compliant else "Non-ULEZ"
    miles_str = f"{car.mileage:,}" if car.mileage else "Low"
    text = (
        f"{car.year} {car.make_model} - £{car.price:,}\n\n"
        f"📍 Location: Luca's Garage, 40 Penrose Street, Walworth, London SE17 3DW\n"
        f"📞 Contact/WhatsApp: {GARAGE_INFO['phone']}\n\n"
        f"KEY DETAILS:\n"
        f"• Mileage: {miles_str} miles\n"
        f"• MOT: {car.mot_expiry or 'Fresh 12 Months'}\n"
        f"• Transmission: {car.TransmissionType}\n"
        f"• Fuel: {car.fuel_type}\n"
        f"• ULEZ Status: {ulez_text}\n"
        f"• Provenance: {car.copart_category}\n\n"
        f"MECHANIC INSPECTION & REPAIRS:\n"
        f"{car.repair_notes or 'Fully inspected, serviced, and road-tested by our mechanics.'}\n\n"
        f"FEATURES:\n"
        f"{car.features or 'Standard features, electric windows, central locking'}\n\n"
        f"Comes with a 30-day mechanical warranty from Luca's Garage. "
        f"Viewings and test drives welcome during opening hours (Mon-Sat). Please message or book to arrange."
    )
    return jsonify({"text": text})

@app.route('/admin/delete/<int:id>', methods=['POST'])
@login_required
def delete_car(id):
    car_to_delete = Car.query.get_or_404(id)
    try:
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], car_to_delete.image_filename)
        if os.path.exists(img_path):
            os.remove(img_path)
    except Exception:
        pass
    db.session.delete(car_to_delete)
    db.session.commit()
    flash('Car removed successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ----------------- DB INITIALIZATION & SEEDING ----------------- #

with app.app_context():
    db.create_all()

    env_admin_username = os.getenv('ADMIN_USER', 'luca')
    env_admin_password = os.getenv('ADMIN_PASSWORD', 'lucasgarage2026')

    if not AdminUser.query.filter_by(username=env_admin_username).first():
        secure_hash = generate_password_hash(env_admin_password)
        seed_admin = AdminUser(username=env_admin_username, password_hash=secure_hash)
        db.session.add(seed_admin)
        db.session.commit()
        print(f"Database initialized with admin account: '{env_admin_username}'")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)