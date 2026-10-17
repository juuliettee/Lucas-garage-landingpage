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


class StoredImage(db.Model):
    __tablename__ = 'stored_images'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, index=True, nullable=False)
    mimetype = db.Column(db.String(100), nullable=False, default='image/jpeg')
    data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CarImage(db.Model):
    __tablename__ = 'car_images'

    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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

    additional_images = db.relationship('CarImage', backref='car', lazy=True, cascade="all, delete-orphan", order_by="CarImage.sort_order, CarImage.id")

    @property
    def all_images(self):
        """Returns a list of image filenames starting with the primary image_filename, followed by any additional images."""
        imgs = []
        if self.image_filename:
            imgs.append(self.image_filename)
        if hasattr(self, 'additional_images') and self.additional_images:
            for extra in self.additional_images:
                if extra.image_filename and extra.image_filename not in imgs:
                    imgs.append(extra.image_filename)
        return imgs if imgs else ([self.image_filename] if self.image_filename else ['logo.png'])

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
            "image_filename": self.image_filename,
            "all_images": self.all_images
        }
