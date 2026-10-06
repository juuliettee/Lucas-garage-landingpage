import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from datetime import datetime, date, timedelta
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

from models import db, Car, AdminUser, Booking, StoredImage, CarImage
from services.whatsapp import (
    generate_customer_whatsapp_url,
    generate_luca_reply_whatsapp_url,
    GARAGE_MOBILE
)
from services.verification import generate_verification_token, verify_booking_token
from services.notifications import send_verification_email, dispatch_confirmed_booking_notifications
from services.calendar_service import create_google_calendar_url

GARAGE_INFO = {
    "name": "Lucas Garage",
    "address": "38a Penrose Street, Walworth, London SE17 3DW",
    "phone": "07535 321145",
    "hours": {
        "monday_to_saturday": "9:00 AM – 6:00 PM",
        "sunday": "Closed"
    },
    "services": "Mechanical repairs, servicing, diagnostics, MOT prep, and quality used car sales."
}

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'default-fallback-dev-key-lucas-garage')
raw_db_url = os.getenv('DATABASE_URL', 'sqlite:///garage.db')
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = raw_db_url
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

def save_uploaded_image(file_storage, prefix="car_"):
    """Saves uploaded image to local disk cache AND persists binary to DB so it survives all future deployments."""
    if not file_storage or not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S_")
    saved_filename = f"{prefix}{timestamp}{filename}"
    file_bytes = file_storage.read()
    if not file_bytes:
        return None

    # 1. Save to disk cache in UPLOAD_FOLDER
    disk_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    try:
        with open(disk_path, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        app.logger.warning(f"Could not write image to local disk cache: {e}")

    # 2. Persist binary in database for resilience across container recycles
    mimetype = file_storage.mimetype or 'image/jpeg'
    try:
        existing = StoredImage.query.filter_by(filename=saved_filename).first()
        if existing:
            existing.data = file_bytes
            existing.mimetype = mimetype
        else:
            db_img = StoredImage(filename=saved_filename, mimetype=mimetype, data=file_bytes)
            db.session.add(db_img)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error persisting image {saved_filename} to database: {e}")
        db.session.rollback()

    return saved_filename

@app.route('/static/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """Serves uploaded vehicle photos from disk, with instant auto-recovery from DB if container was recreated."""
    disk_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(disk_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Rehydrate from database if missing on ephemeral filesystem
    try:
        stored = StoredImage.query.filter_by(filename=filename).first()
        if stored and stored.data:
            try:
                with open(disk_path, 'wb') as f:
                    f.write(stored.data)
            except Exception:
                pass
            return send_file(BytesIO(stored.data), mimetype=stored.mimetype or 'image/jpeg')
    except Exception as e:
        app.logger.error(f"Error retrieving image {filename} from DB: {e}")

    # Fallback to Hyundai i10 or default logo so prelisted cars NEVER show broken 404 image icons
    fallback_i10 = os.path.join(app.config['UPLOAD_FOLDER'], '20261006185331_i10.webp')
    if os.path.exists(fallback_i10):
        return send_from_directory(app.config['UPLOAD_FOLDER'], '20261006185331_i10.webp')
    fallback_logo = os.path.join(app.root_path, 'static', 'img', 'logo.png')
    if os.path.exists(fallback_logo):
        return send_from_directory(os.path.join(app.root_path, 'static', 'img'), 'logo.png')
    return "Image not found", 404

# Context processor for templates to always have garage info & direct WhatsApp
@app.context_processor
def inject_garage_data():
    return {
        "garage_info": GARAGE_INFO,
        "garage_mobile": GARAGE_MOBILE,
        "default_whatsapp_url": generate_customer_whatsapp_url()
    }

@app.template_filter('format_date_dmy')
def format_date_dmy(date_val):
    if not date_val:
        return ""
    date_str = str(date_val)
    if "-" in date_str:
        parts = date_str.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return date_str

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

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

# ----------------- BOOKING & VERIFICATION ROUTES ----------------- #

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
        return jsonify({"success": False, "message": "Please fill in your Name, Phone number, Date, and Time."}), 400

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
            return jsonify({"success": False, "message": "The garage is closed on Sundays. Please choose Monday through Saturday between 9:00 AM and 6:00 PM."}), 400
        elif time_decimal < 9.0 or time_decimal > 17.5:
            return jsonify({"success": False, "message": "Opening hours are Monday to Saturday 9:00 AM – 6:00 PM. Please choose a slot between 09:00 and 17:30."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Invalid date or time format: {e}"}), 400

    # Save directly as Confirmed (Frictionless for 5-6 man garage)
    booking = Booking(
        car_id=car.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email or "Not provided",
        booking_date=booking_date,
        booking_time=booking_time,
        notes=notes,
        status="Confirmed"
    )
    db.session.add(booking)
    db.session.commit()

    # Generate 1-tap Google Calendar link
    gcal_url = create_google_calendar_url(
        car.make_model, booking_date, booking_time, customer_name, customer_phone
    )

    # 1-Tap WhatsApp direct confirmation URL with full booking details
    import urllib.parse
    dmy_date = booking_date
    if booking_date and "-" in booking_date:
        parts = booking_date.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            dmy_date = f"{parts[2]}/{parts[1]}/{parts[0]}"

    booking_msg = (
        f"Hi Luca, I just booked a viewing for the {car.year} {car.make_model} "
        f"on {dmy_date} at {booking_time}. My name is {customer_name} ({customer_phone}). "
        f"Booking Ref: #LG-{booking.id}"
    )
    whatsapp_url = f"https://wa.me/{GARAGE_MOBILE}?text={urllib.parse.quote(booking_msg)}"

    # Multi-channel alerts (Buyer email if provided, Luca alert email/telegram)
    try:
        dispatch_confirmed_booking_notifications(booking, car)
    except Exception as e:
        app.logger.warning(f"Notification alert notice: {e}")

    return jsonify({
        "success": True,
        "booking_id": booking.id,
        "booking_ref": f"#LG-{booking.id}",
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "booking_date": booking_date,
        "booking_time": booking_time,
        "car_name": f"{car.year} {car.make_model}",
        "gcal_url": gcal_url,
        "whatsapp_url": whatsapp_url,
        "message": f"Viewing confirmed for {booking_date} at {booking_time}!"
    })


@app.route('/booking/verify')
def verify_booking():
    token = request.args.get('token')
    if not token:
        return render_template('booking_confirmed.html', success=False, error_msg="Missing confirmation token.")

    is_valid, data_or_err = verify_booking_token(token)
    if not is_valid:
        return render_template('booking_confirmed.html', success=False, error_msg=data_or_err)

    booking = Booking.query.filter_by(verification_token=token).first()
    if not booking:
        return render_template('booking_confirmed.html', success=False, error_msg="Booking reference not found.")

    car = booking.car or Car.query.get(booking.car_id)

    if booking.status == "Confirmed":
        gcal_url = create_google_calendar_url(car.make_model, booking.booking_date, booking.booking_time, booking.customer_name, booking.customer_phone)
        whatsapp_url = generate_customer_whatsapp_url(car_name=f"{car.year} {car.make_model}", message_type="viewing")
        return render_template('booking_confirmed.html', success=True, booking=booking, car=car, gcal_url=gcal_url, customer_whatsapp_url=whatsapp_url)

    # Check for double-booking conflict
    conflict = Booking.query.filter(
        Booking.car_id == booking.car_id,
        Booking.booking_date == booking.booking_date,
        Booking.booking_time == booking.booking_time,
        Booking.status == "Confirmed",
        Booking.id != booking.id
    ).first()
    if conflict:
        booking.status = "Cancelled"
        db.session.commit()
        return render_template('booking_confirmed.html', success=False, error_msg="Another buyer just confirmed this slot. Please choose another time.")

    # Flip status to Confirmed
    booking.status = "Confirmed"
    db.session.commit()

    # Trigger multi-channel alerts (Buyer .ics calendar, Luca .ics calendar, and Telegram)
    try:
        dispatch_confirmed_booking_notifications(booking, car)
    except Exception as e:
        app.logger.warning(f"Notification dispatch error: {e}")

    gcal_url = create_google_calendar_url(car.make_model, booking.booking_date, booking.booking_time, booking.customer_name, booking.customer_phone)
    whatsapp_url = generate_customer_whatsapp_url(car_name=f"{car.year} {car.make_model}", message_type="viewing")

    return render_template('booking_confirmed.html', success=True, booking=booking, car=car, gcal_url=gcal_url, customer_whatsapp_url=whatsapp_url)

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

@app.route('/admin/test-email')
@login_required
def admin_test_email():
    from services.notifications import send_email, LUCA_EMAIL, SMTP_USER, SMTP_PASS
    resend_key = os.getenv("RESEND_API_KEY")
    if not (SMTP_USER and SMTP_PASS) and not resend_key:
        flash("Email alert not sent: SMTP_USER and SMTP_PASS (or RESEND_API_KEY) are not yet configured in your .env file.", "danger")
        return redirect(url_for('admin_dashboard'))

    test_subject = "Test Booking Alert - Lucas Garage"
    test_body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
        <h2 style="color: #0b1117;">Lucas Garage Email Alert Test</h2>
        <p>This test email confirms your mailbox is properly connected to the Lucas Garage website.</p>
        <p>Whenever a customer books a vehicle viewing, you will automatically receive an email alert with the customer's name, phone number, car, and appointment date/time.</p>
    </div>
    """
    success = send_email(LUCA_EMAIL, test_subject, test_body)
    if success:
        flash(f"Test email successfully dispatched to {LUCA_EMAIL}!", "success")
    else:
        flash(f"Failed to deliver email to {LUCA_EMAIL}. Please verify your credentials in .env.", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add', methods=['POST'])
@login_required
def add_car():
    make_model = request.form.get('make_model')
    year = int(request.form.get('year', 2018))
    price = int(request.form.get('price', 0))
    TransmissionType = request.form.get('TransmissionType', 'Manual')
    fuel_type = request.form.get('fuel_type', 'Petrol')
    
    mileage = int(request.form.get('mileage') or 0)
    ulez_compliant = True if request.form.get('ulez_compliant') == 'on' else False
    mot_expiry = request.form.get('mot_expiry', '12 Months MOT')
    copart_category = request.form.get('copart_category', 'Clean / Unrecorded')
    repair_notes = request.form.get('repair_notes', '')
    features = request.form.get('features', '')

    # Support multiple file uploads
    uploaded_files = request.files.getlist('images')
    if not uploaded_files or not any(getattr(f, 'filename', '') for f in uploaded_files):
        single_file = request.files.get('image')
        if single_file and single_file.filename:
            uploaded_files = [single_file]

    saved_filenames = []
    for f in uploaded_files:
        if f and getattr(f, 'filename', '') and allowed_file(f.filename):
            saved = save_uploaded_image(f)
            if saved:
                saved_filenames.append(saved)

    if not saved_filenames:
        flash('Please upload at least one valid vehicle photo (JPG, PNG, or WebP).', 'danger')
        return redirect(url_for('admin_dashboard'))

    primary_image = saved_filenames[0]
    new_car = Car(
        make_model=make_model,
        year=year,
        price=price,
        TransmissionType=TransmissionType,
        fuel_type=fuel_type,
        image_filename=primary_image,
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

    # Store any extra photos in CarImage
    for extra_file in saved_filenames[1:]:
        db.session.add(CarImage(car_id=new_car.id, image_filename=extra_file))
    if len(saved_filenames) > 1:
        db.session.commit()

    flash(f'Vehicle "{make_model}" listed successfully with {len(saved_filenames)} photo(s)!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/car/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_car(id):
    car = Car.query.get_or_404(id)
    if request.method == 'POST':
        car.make_model = request.form.get('make_model', car.make_model).strip()
        car.year = int(request.form.get('year', car.year))
        car.price = int(request.form.get('price', car.price))
        car.TransmissionType = request.form.get('TransmissionType', car.TransmissionType)
        car.fuel_type = request.form.get('fuel_type', car.fuel_type)
        car.mileage = int(request.form.get('mileage') or 0)
        car.ulez_compliant = True if request.form.get('ulez_compliant') == 'on' else False
        car.mot_expiry = request.form.get('mot_expiry', car.mot_expiry).strip()
        car.copart_category = request.form.get('copart_category', car.copart_category).strip()
        car.repair_notes = request.form.get('repair_notes', '').strip()
        car.features = request.form.get('features', '').strip()
        new_status = request.form.get('status', car.status)
        if new_status in ['Available', 'Reserved', 'Sold']:
            car.status = new_status

        # Handle newly uploaded additional photos
        new_files = request.files.getlist('new_images')
        new_saved_count = 0
        for f in new_files:
            if f and getattr(f, 'filename', '') and allowed_file(f.filename):
                saved = save_uploaded_image(f)
                if saved:
                    if not car.image_filename:
                        car.image_filename = saved
                    else:
                        db.session.add(CarImage(car_id=car.id, image_filename=saved))
                    new_saved_count += 1

        db.session.commit()
        msg = f'Listing for "{car.make_model}" updated successfully!'
        if new_saved_count > 0:
            msg += f' Added {new_saved_count} new photo(s).'
        flash(msg, 'success')
        return redirect(url_for('edit_car', id=car.id))

    return render_template('edit_car.html', car=car)

@app.route('/admin/car/<int:id>/set-cover/<path:filename>', methods=['POST'])
@login_required
def set_car_cover_image(id, filename):
    car = Car.query.get_or_404(id)
    if car.image_filename != filename:
        old_cover = car.image_filename
        target_img = CarImage.query.filter_by(car_id=car.id, image_filename=filename).first()
        if target_img:
            db.session.delete(target_img)
        if old_cover:
            existing_old = CarImage.query.filter_by(car_id=car.id, image_filename=old_cover).first()
            if not existing_old:
                db.session.add(CarImage(car_id=car.id, image_filename=old_cover))
        car.image_filename = filename
        db.session.commit()
        flash('Primary cover photo updated!', 'success')
    return redirect(url_for('edit_car', id=car.id))

@app.route('/admin/car/<int:id>/delete-image/<path:filename>', methods=['POST'])
@login_required
def delete_car_image(id, filename):
    car = Car.query.get_or_404(id)
    target_img = CarImage.query.filter_by(car_id=car.id, image_filename=filename).first()
    if target_img:
        db.session.delete(target_img)
        db.session.commit()
        flash('Photo removed from vehicle listing.', 'info')
    elif car.image_filename == filename:
        next_img = CarImage.query.filter_by(car_id=car.id).first()
        if next_img:
            car.image_filename = next_img.image_filename
            db.session.delete(next_img)
            db.session.commit()
            flash('Cover photo removed; next photo promoted to cover.', 'info')
        else:
            flash('Cannot remove the only photo. Upload a replacement photo first.', 'warning')
    return redirect(url_for('edit_car', id=car.id))

@app.route('/admin/status/<int:id>/<string:new_status>', methods=['POST'])
@login_required
def update_status(id, new_status):
    car = Car.query.get_or_404(id)
    if new_status in ['Available', 'Reserved', 'Sold']:
        car.status = new_status
        db.session.commit()
        flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/booking/edit/<int:id>', methods=['POST'])
@login_required
def edit_booking(id):
    booking = Booking.query.get_or_404(id)
    booking_date = request.form.get('booking_date', '').strip()
    booking_time = request.form.get('booking_time', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    customer_email = request.form.get('customer_email', '').strip()
    status = request.form.get('status', '').strip()
    notes = request.form.get('notes', '').strip()

    if booking_date:
        booking.booking_date = booking_date
    if booking_time:
        booking.booking_time = booking_time
    if customer_phone:
        booking.customer_phone = customer_phone
    if customer_email:
        booking.customer_email = customer_email
    if status in ['Confirmed', 'Pending_Verification', 'Completed', 'Cancelled']:
        booking.status = status
    booking.notes = notes

    db.session.commit()
    flash(f'Viewing appointment for {booking.customer_name} updated successfully!', 'success')
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
        f"📍 Location: Lucas Garage, 38a Penrose Street, Walworth, London SE17 3DW\n"
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
        f"Comes with a 30-day mechanical warranty & 3-month workshop labour guarantee from Lucas Garage. "
        f"Viewings welcome during opening hours (Mon-Sat). Please message or book to arrange."
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