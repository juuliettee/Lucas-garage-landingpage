"""
Seeds realistic used & Copart-repaired vehicles for Luca's Garage.
"""
from app import app
from models import db, Car, AdminUser, Booking
from werkzeug.security import generate_password_hash
from datetime import date, timedelta

with app.app_context():
    db.create_all()

    # Seed Admin User
    if not AdminUser.query.filter_by(username='luca').first():
        admin = AdminUser(username='luca', password_hash=generate_password_hash('lucasgarage2026'))
        db.session.add(admin)
        print("Created admin user 'luca'")

    # Seed Cars if empty
    if Car.query.count() == 0:
        car1 = Car(
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
        )

        car2 = Car(
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
        )

        car3 = Car(
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

        db.session.add_all([car1, car2, car3])
        db.session.commit()
        print("Seeded 3 sample cars.")

        # Seed sample booking
        sample_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        booking = Booking(
            car_id=car1.id,
            customer_name="Mark Davies",
            customer_phone="07700 900123",
            customer_email="mark.davies@example.co.uk",
            booking_date=sample_date,
            booking_time="14:30",
            notes="Interested in test driving the Focus and checking the wing repair on the lift.",
            status="Confirmed"
        )
        db.session.add(booking)
        db.session.commit()
        print("Seeded sample booking.")

print("Database seeding completed.")
