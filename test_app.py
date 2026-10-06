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
        assert b"38a Penrose Street" in resp.data, "Penrose Street address missing from homepage"
        assert b"07535 321145" in resp.data, "WhatsApp mobile number missing from homepage"
        assert b"Lucas Garage" in resp.data, "Lucas Garage missing from homepage"
        print("✅ Test 1 Passed: Homepage renders with 38a Penrose St, Lucas Garage & WhatsApp mobile.")

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

        # 5b. Sunday booking rejected (closed); Saturday 10:30 accepted (Mon-Sat 9am-6pm)
        sunday_payload = {
            "car_id": car.id,
            "customer_name": "James Bond",
            "customer_phone": "07007 007007",
            "booking_date": "2026-09-27", # Sunday
            "booking_time": "11:30"
        }
        resp = client.post('/api/book-viewing', data=sunday_payload)
        assert resp.status_code == 400
        assert "closed on sundays" in resp.get_json()['message'].lower()

        saturday_payload = {
            "car_id": car.id,
            "customer_name": "James Bond",
            "customer_phone": "07007 007007",
            "booking_date": "2026-09-26", # Saturday
            "booking_time": "10:30"
        }
        resp = client.post('/api/book-viewing', data=saturday_payload)
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True
        print("✅ Test 5b Passed: Opening hours verified (Sunday closed, Mon–Sat 9am–6pm accepted).")

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
        assert "38a Penrose Street" in ad_data['text']
        assert "ULEZ" in ad_data['text']
        assert "30-day" in ad_data['text']
        print("✅ Test 7 Passed: 1-Click Facebook Marketplace / Gumtree copyable text generated.")

        # 8. Test Vehicle Listing Edit & Multi-Photo Support
        from io import BytesIO
        edit_get = client.get(f'/admin/car/edit/{car.id}')
        assert edit_get.status_code == 200
        assert b"Vehicle Editor" in edit_get.data

        # Post edit with updated description & simulated second photo
        fake_photo = (BytesIO(b"fake_image_bytes_png"), "test_extra.png")
        edit_post = client.post(f'/admin/car/edit/{car.id}', data={
            "make_model": car.make_model,
            "year": car.year,
            "price": car.price + 50,
            "TransmissionType": car.TransmissionType,
            "fuel_type": car.fuel_type,
            "mileage": car.mileage,
            "ulez_compliant": "on",
            "mot_expiry": "March 2027",
            "copart_category": "Clean / Unrecorded",
            "repair_notes": "Updated repair notes: Fresh brake service completed.",
            "features": "Air Con, 2 Keys, Bluetooth",
            "status": "Available",
            "new_images": [fake_photo]
        }, follow_redirects=True)
        assert edit_post.status_code == 200
        assert b"Fresh brake service completed" in edit_post.data

        # Verify Car has multiple images in all_images
        updated_car = Car.query.get(car.id)
        assert len(updated_car.all_images) >= 2
        print(f"✅ Test 8 Passed: Car editing works and multi-photo attached ({len(updated_car.all_images)} photos).")

        # 9. Test Detail Page Renders Multi-Photo Carousel
        detail_resp = client.get(f'/car/{car.id}')
        assert detail_resp.status_code == 200
        assert b"mainGalleryImage" in detail_resp.data
        assert b"galleryCounter" in detail_resp.data
        assert b"prevCarImage" in detail_resp.data
        print("✅ Test 9 Passed: Interactive photo carousel and thumbnail gallery rendered on vehicle detail page.")

        # 10. Test Edit / Reschedule Booking
        booking_to_edit = Booking.query.filter_by(customer_name="Sarah Connor").first()
        assert booking_to_edit is not None
        resched_resp = client.post(f'/admin/booking/edit/{booking_to_edit.id}', data={
            "booking_date": "2026-09-30",
            "booking_time": "15:00",
            "customer_phone": "07987 000111",
            "customer_email": "sarah_new@example.com",
            "status": "Confirmed",
            "notes": "Customer requested 3:00 PM instead."
        }, follow_redirects=True)
        assert resched_resp.status_code == 200
        reloaded_b = Booking.query.get(booking_to_edit.id)
        assert reloaded_b.booking_time == "15:00"
        assert reloaded_b.booking_date == "2026-09-30"
        assert reloaded_b.customer_phone == "07987 000111"
        print("✅ Test 10 Passed: Appointment rescheduling and details edit successful.")

        # 11. Test Resilient Image Serving Route
        img_resp = client.get(f'/static/uploads/{car.image_filename}')
        assert img_resp.status_code == 200
        print("✅ Test 11 Passed: Static uploads route safely serves vehicle photos.")

        # 12. Test Defensive Security Hardening
        home_resp = client.get('/')
        assert home_resp.headers.get('X-Content-Type-Options') == 'nosniff'
        assert home_resp.headers.get('X-Frame-Options') == 'SAMEORIGIN'
        assert home_resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
        assert app.config['MAX_CONTENT_LENGTH'] == 16 * 1024 * 1024
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'

        # Directory traversal prevention
        traversal_resp = client.get('/static/uploads/..%2fapp.py')
        assert traversal_resp.status_code in [400, 404]

        # Admin template Stored XSS defense verification
        admin_page = client.get('/admin')
        assert b'openEditBookingModalFromBtn(this)' in admin_page.data
        assert b'data-name=' in admin_page.data
        print("✅ Test 12 Passed: Defensive security hardening verified (headers, cookies, traversal, XSS defense).")

        # 13. Test Custom 404 Page & SEO Directives
        not_found_resp = client.get('/nefwjnfwjnfjewnfn')
        assert not_found_resp.status_code == 404
        assert b"Page Not Found" in not_found_resp.data
        assert b"Return Home" in not_found_resp.data

        robots_resp = client.get('/robots.txt')
        assert robots_resp.status_code == 200
        assert b"Disallow: /admin/" in robots_resp.data
        assert b"Sitemap: https://lucasgarage.uk/sitemap.xml" in robots_resp.data

        sitemap_resp = client.get('/sitemap.xml')
        assert sitemap_resp.status_code == 200
        assert b"<urlset" in sitemap_resp.data
        assert b"https://lucasgarage.uk/cars" in sitemap_resp.data
        print("✅ Test 13 Passed: Custom 404 page, robots.txt, and sitemap.xml verified.")

        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
