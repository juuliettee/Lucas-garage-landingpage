"""
Lucas Garage Dummy Data Seeder.
Populates the database with realistic sample vehicles and test appointments.
"""
import os
import sys
import json
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db, Car, AdminUser

def seed_database():
    """Seeds realistic demo data into the active database."""
    with app.app_context():
        db.create_all()

        # 1. Seed Admin User
        admin_username = os.getenv('ADMIN_USER', 'luca')
        admin_password = os.getenv('ADMIN_PASSWORD', 'lucasgarage2026')
        if not AdminUser.query.filter_by(username=admin_username).first():
            admin = AdminUser(username=admin_username, password_hash=generate_password_hash(admin_password))
            db.session.add(admin)
            print(f"Created admin user '{admin_username}'")

        # 2. Seed Cars from cars.json if empty
        if Car.query.count() == 0:
            json_path = os.path.join(os.path.dirname(__file__), 'cars.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    car_records = json.load(f)
                cars = [Car(**item) for item in car_records]
            else:
                cars = [
                    Car(
                        make_model="Ford Focus 1.0 EcoBoost Titanium",
                        year=2018,
                        price=6995,
                        TransmissionType="Manual",
                        fuel_type="Petrol",
                        image_filename="ford_focus.jpg",
                        mileage=52400,
                        ulez_compliant=True,
                        mot_expiry="March 2027 (12 Months)",
                        copart_category="Cat N (Non-structural cosmetic repair)",
                        repair_notes="Sourced with non-structural passenger front wing and bumper scuff. Replaced with genuine Ford OEM wing panel, freshly resprayed to factory color match. Full major service completed (new oil, spark plugs, air/cabin filters, and front brake pads). Road-tested for 150 miles.",
                        features="SYNC 3 Touchscreen with Apple CarPlay, Rear Parking Sensors, Cruise Control, Dual Climate, Keyless Start",
                        status="Available"
                    ),
                    Car(
                        make_model="Volkswagen Golf 1.4 TSI Match Edition",
                        year=2017,
                        price=8450,
                        TransmissionType="Automatic",
                        fuel_type="Petrol",
                        image_filename="vw_golf.jpg",
                        mileage=61200,
                        ulez_compliant=True,
                        mot_expiry="November 2026",
                        copart_category="Clean / Unrecorded",
                        repair_notes="Clean title. Workshop repairs: Replaced rear brake discs & pads, refreshed DSG transmission oil, brand new Michelin front tires, full alignment on hunter rack.",
                        features="Adaptive Cruise Control, Front & Rear Sensors, Heated Front Seats, Discover Navigation, Bluetooth",
                        status="Available"
                    ),
                    Car(
                        make_model="Vauxhall Corsa 1.4 ecoFLEX Energy",
                        year=2019,
                        price=5750,
                        TransmissionType="Manual",
                        fuel_type="Petrol",
                        image_filename="vauxhall_corsa.jpg",
                        mileage=43100,
                        ulez_compliant=True,
                        mot_expiry="October 2026",
                        copart_category="Cat N (Light plastic bumper repair)",
                        repair_notes="Light cosmetic rear bumper damage from auction. Repaired and resprayed. Full diagnostics cleared, new 12V Bosch battery fitted, air conditioning freshly re-gassed.",
                        features="Heated Steering Wheel & Seats, City Steering Mode, Touchscreen Bluetooth, Alloy Wheels",
                        status="Available"
                    )
                ]

            db.session.add_all(cars)
            db.session.commit()
            print(f"Seeded {len(cars)} sample cars.")

        print("Database seeding completed successfully.")

if __name__ == '__main__':
    seed_database()
