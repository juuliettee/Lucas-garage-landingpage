# Model definitions for lucas garage landing page application.
#  This is for the database models, if needed in the future such as for uploading car images prices etc
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
