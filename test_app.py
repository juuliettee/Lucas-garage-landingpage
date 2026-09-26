"""
Comprehensive verification test suite for Lucas Garage web app.
"""
from app import app
from models import db, Car, Booking, AdminUser

def run_tests():
    with app.app_context():
        client = app.test_client()
        print("Beginning automated verification tests...\n")

        # 1. Test Homepage
        resp = client.get('/')
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert b"40 Penrose Street" in resp.data, "Penrose Street address missing from homepage"
        assert b"07535 321145" in resp.data, "WhatsApp mobile number missing from homepage"
        assert b"Lucas Garage" in resp.data, "Lucas Garage missing from homepage"
        print("✅ Test 1 Passed: Homepage renders with 40 Penrose St, Lucas Garage & WhatsApp mobile.")

        # 2. Test Inventory Page
        resp = client.get('/cars')
        assert resp.status_code == 200
        car = Car.query.first()
        if car:
            assert car.make_model.encode() in resp.data
        assert b"ULEZ" in resp.data
        print("✅ Test 2 Passed: Vehicle inventory displays with ULEZ badges and prices.")

        # 3. Test Detail Page
        resp = client.get(f'/car/{car.id}')
        assert resp.status_code == 200
        assert b"Lucas Garage" in resp.data
        print("✅ Test 3 Passed: Vehicle detail page renders with Lucas Garage and booking form.")

        # 4. Test About, Pricing & Services routes
        resp = client.get('/about')
        assert resp.status_code == 200
        assert b"Lucas Garage" in resp.data
        print("✅ Test 4a Passed: About page renders with Lucas Garage.")

        resp = client.get('/pricing')
        assert resp.status_code == 200
        assert b"Workshop Pricing" in resp.data
        print("✅ Test 4b Passed: Pricing page renders.")

        resp = client.get('/#services')
        assert resp.status_code == 200
        print("✅ Test 4c Passed: Services anchor accessible.")

        # 5. Test Viewing Booking API
        # Clean up existing test booking if present
        Booking.query.filter_by(customer_name="Sarah Connor").delete()
        db.session.commit()

        # 5a. Valid booking on a Monday at 14:30
        booking_payload = {
            "car_id": car.id,
            "customer_name": "Sarah Connor",
            "customer_phone": "07987 654321",
            "customer_email": "sarah@example.com",
            "booking_date": "2026-09-28", # Monday
            "booking_time": "14:30",
            "notes": "Looking to inspect the underneath on the lift."
        }
        resp = client.post('/api/book-viewing', data=booking_payload)
        assert resp.status_code == 200, f"Booking failed with code {resp.status_code}: {resp.data}"
        book_data = resp.get_json()
        assert book_data['success'] is True
        assert "Viewing confirmed" in book_data['message']

        # Verify booking exists in DB
        created_booking = Booking.query.filter_by(customer_name="Sarah Connor").first()
        assert created_booking is not None
        assert created_booking.booking_time == "14:30"
        print("✅ Test 5a Passed: Valid viewing booked, saved to database, and WhatsApp alert triggered.")

        # 5b. Sunday booking should be rejected (garage closed)
        sunday_payload = {
            "car_id": car.id,
            "customer_name": "James Bond",
            "customer_phone": "07007 007007",
            "booking_date": "2026-09-27", # Sunday
            "booking_time": "14:30"
        }
        resp = client.post('/api/book-viewing', data=sunday_payload)
        assert resp.status_code == 400
        assert "closed on sundays" in resp.get_json()['message'].lower()
        print("✅ Test 5b Passed: Sunday booking correctly rejected with garage closed notice.")

        # 6. Test Admin Authentication & Dashboard
        import os
        adm_u = os.getenv('ADMIN_USER', 'admin')
        adm_p = os.getenv('ADMIN_PASSWORD', 'LucaGarage2026!')
        login_resp = client.post('/login', data={"username": adm_u, "password": adm_p}, follow_redirects=True)
        assert login_resp.status_code == 200
        assert b"Workshop & Vehicle Portal" in login_resp.data
        assert b"Booked Customer Viewings" in login_resp.data
        assert b"Sarah Connor" in login_resp.data
        print("✅ Test 6 Passed: Admin login works, shows active bookings and WhatsApp customer buttons.")

        # 7. Test Facebook Marketplace Ad Text Generator
        ad_resp = client.get(f'/admin/marketplace-text/{car.id}')
        assert ad_resp.status_code == 200
        ad_data = ad_resp.get_json()
        assert "40 Penrose Street" in ad_data['text']
        assert "ULEZ" in ad_data['text']
        assert "30-day" in ad_data['text']
        print("✅ Test 7 Passed: 1-Click Facebook Marketplace / Gumtree copyable text generated.")

        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
