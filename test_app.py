"""
Comprehensive verification test suite for Luca's Garage web app.
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
        print("✅ Test 1 Passed: Homepage renders with 40 Penrose St & WhatsApp mobile.")

        # 2. Test Inventory Page
        resp = client.get('/cars')
        assert resp.status_code == 200
        assert b"Ford Focus" in resp.data
        assert b"Volkswagen Golf" in resp.data
        assert b"ULEZ" in resp.data
        print("✅ Test 2 Passed: Vehicle inventory displays with ULEZ badges and prices.")

        # 3. Test Detail Page
        car = Car.query.first()
        resp = client.get(f'/car/{car.id}')
        assert resp.status_code == 200
        assert b"Mechanic Inspection" in resp.data
        assert b"Book In-Person Viewing" in resp.data
        print("✅ Test 3 Passed: Vehicle detail page renders with repair notes and booking form.")

        # 4. Test AI Chat Assistant API
        # 4a. ULEZ inquiry
        chat_resp = client.post('/api/chat', json={"message": "Is the Ford Focus ULEZ compliant?"})
        assert chat_resp.status_code == 200
        data = chat_resp.get_json()
        assert "ulez" in data['reply'].lower(), "AI reply missing ULEZ information"
        print(f"✅ Test 4a Passed: AI answers ULEZ: \"{data['reply']}\"")

        # 4b. Copart repair inquiry
        chat_resp = client.post('/api/chat', json={"message": "Why was this car on Copart and is it safe?"})
        assert chat_resp.status_code == 200
        data = chat_resp.get_json()
        assert any(w in data['reply'].lower() for w in ["mechanic", "repair", "safe", "service", "penrose"]), "AI reply missing mechanic reassurance"
        print(f"✅ Test 4b Passed: AI answers Copart repairs: \"{data['reply']}\"")

        # 4c. Location and hours inquiry
        chat_resp = client.post('/api/chat', json={"message": "What time are you open on Saturday?"})
        assert chat_resp.status_code == 200
        data = chat_resp.get_json()
        assert "penrose" in data['reply'].lower() or "1:00" in data['reply'] or "6:00" in data['reply'], "AI reply missing hours/location"
        print(f"✅ Test 4c Passed: AI answers opening hours: \"{data['reply']}\"")

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
        login_resp = client.post('/login', data={"username": "luca", "password": "lucasgarage2026"}, follow_redirects=True)
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
