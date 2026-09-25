# Model definitions for Lucas Garage landing page & sales assistant
from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash

db = SQLAlchemy()

class AdminUser(db.Model, UserMixin):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Car(db.Model):
    __tablename__ = 'cars'

    id = db.Column(db.Integer, primary_key=True)
    make_model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    TransmissionType = db.Column(db.String(100), nullable=False)
    fuel_type = db.Column(db.String(100), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    
    # Rich fields for buyer trust and Copart repair transparency
    mileage = db.Column(db.Integer, nullable=True, default=0)
    ulez_compliant = db.Column(db.Boolean, nullable=False, default=True)
    mot_expiry = db.Column(db.String(50), nullable=True) # e.g. "October 2026" or "12 Months MOT"
    copart_category = db.Column(db.String(100), nullable=True, default="Clean / Unrecorded")
    repair_notes = db.Column(db.Text, nullable=True)
    features = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Available") # Available, Reserved, Sold
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='car', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "make_model": self.make_model,
            "year": self.year,
            "price": self.price,
            "transmission": self.TransmissionType,
            "fuel_type": self.fuel_type,
            "mileage": self.mileage or "Not specified",
            "ulez_compliant": "Yes (Exempt)" if self.ulez_compliant else "No",
            "mot_expiry": self.mot_expiry or "Fresh MOT included",
            "copart_category": self.copart_category or "Clean / Unrecorded",
            "repair_notes": self.repair_notes or "Fully inspected, serviced, and road-tested by mechanic.",
            "features": self.features or "Standard spec",
            "status": self.status,
            "image_filename": self.image_filename
        }


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    booking_date = db.Column(db.String(20), nullable=False) # Format: YYYY-MM-DD
    booking_time = db.Column(db.String(20), nullable=False) # Format: HH:MM
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Pending_Verification") # Pending_Verification, Confirmed, Completed, Cancelled
    verification_token = db.Column(db.String(255), unique=True, index=True, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_token_valid(self):
        return (
            self.status == 'Pending_Verification' and
            self.token_expires_at and
            datetime.utcnow() <= self.token_expires_at
        )

    def to_dict(self):
        return {
            "id": self.id,
            "car_id": self.car_id,
            "car_name": self.car.make_model if self.car else "Vehicle",
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "customer_email": self.customer_email or "",
            "booking_date": self.booking_date,
            "booking_time": self.booking_time,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
        }
