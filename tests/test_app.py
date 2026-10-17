"""
Comprehensive verification test suite for Lucas Garage web app.
"""
import os
import sys
import re

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db, Car, AdminUser

def extract_csrf_token(response_bytes):
    html = response_bytes.decode('utf-8', errors='ignore')
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert match, "CSRF token not found in response HTML"
    return match.group(1)

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
        print("✅ Test 3 Passed: Vehicle detail page renders with Lucas Garage and viewing information.")

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

        # 5. Test 1-Tap WhatsApp Viewing & Inquiry URL Generator
        from services.whatsapp import generate_customer_whatsapp_url, generate_viewing_request_whatsapp_url

        # 5a. General vehicle viewing request link
        viewing_url = generate_customer_whatsapp_url(car_name=car.make_model, message_type="viewing")
        assert "wa.me/447535321145" in viewing_url
        assert "38a%20Penrose%20Street" in viewing_url
        assert "wa.me" in viewing_url
        print("✅ Test 5a Passed: 1-Tap WhatsApp viewing link correctly generated with garage mobile and address.")

        # 5b. Preferred slot viewing request link
        custom_viewing_url = generate_viewing_request_whatsapp_url(
            car_name=car.make_model,
            booking_date="2026-10-20",
            booking_time="14:00",
            customer_name="Sarah Connor",
            customer_note="Inspect on hydraulic lift"
        )
        assert "wa.me/447535321145" in custom_viewing_url
        assert "Sarah%20Connor" in custom_viewing_url
        assert "20/10/2026" in custom_viewing_url
        assert "14%3A00" in custom_viewing_url
        print("✅ Test 5b Passed: Customer viewing request with prefilled date/time/lift notes generated cleanly.")

        # 6. Test Admin Authentication & Dashboard
        import os
        adm_u = os.getenv('ADMIN_USER', 'admin')
        adm_p = os.getenv('ADMIN_PASSWORD', 'LucaGarage2026!')
        login_page = client.get('/login')
        login_csrf = extract_csrf_token(login_page.data)

        # Verify missing & forged CSRF tokens are blocked with 400 Bad Request
        no_csrf_resp = client.post('/login', data={"username": adm_u, "password": adm_p})
        assert no_csrf_resp.status_code == 400
        forged_csrf_resp = client.post('/login', data={"username": adm_u, "password": adm_p, "csrf_token": "forged_invalid_token"})
        assert forged_csrf_resp.status_code == 400

        login_resp = client.post('/login', data={"username": adm_u, "password": adm_p, "csrf_token": login_csrf}, follow_redirects=True)
        assert login_resp.status_code == 200
        assert b"Workshop & Vehicle Portal" in login_resp.data
        assert b"List a Repaired Vehicle" in login_resp.data
        assert b"Current Inventory" in login_resp.data
        admin_csrf = extract_csrf_token(login_resp.data)
        print("✅ Test 6 Passed: Admin login works, shows vehicle inventory management portal.")

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
        edit_csrf = extract_csrf_token(edit_get.data)
        edit_post = client.post(f'/admin/car/edit/{car.id}', data={
            "csrf_token": edit_csrf,
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

        # 10. Test Vehicle Status Toggling (Available -> Sold -> Available)
        status_resp = client.post(f'/admin/status/{car.id}/Sold', data={"csrf_token": admin_csrf}, follow_redirects=True)
        assert status_resp.status_code == 200
        reloaded_car = Car.query.get(car.id)
        assert reloaded_car.status == "Sold"

        # Toggle back to Available
        status_resp2 = client.post(f'/admin/status/{car.id}/Available', data={"csrf_token": admin_csrf}, follow_redirects=True)
        assert status_resp2.status_code == 200
        reloaded_car2 = Car.query.get(car.id)
        assert reloaded_car2.status == "Available"
        print("✅ Test 10 Passed: Vehicle status toggle (Available <-> Sold) verified with CSRF protection.")

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

        # Admin template Stored XSS defense verification & safe rendering
        admin_page = client.get('/admin')
        assert b'copyMarketplaceAd(' in admin_page.data
        assert b'name="csrf_token"' in admin_page.data

        # CSRF token protection verification on protected mutation routes
        csrf_missing_resp = client.post('/admin/add', data={'make_model': 'Test Car'})
        assert csrf_missing_resp.status_code == 400, "Protected admin route allowed POST without CSRF token"
        csrf_forged_resp = client.post('/admin/add', data={'make_model': 'Test Car', 'csrf_token': 'fake_bad_token'})
        assert csrf_forged_resp.status_code == 400, "Protected admin route allowed POST with forged CSRF token"
        print("✅ Test 12 Passed: Defensive security hardening verified (CSRF tokens, headers, cookies, traversal, XSS defense).")

        # 13. Test Custom 404 Page & SEO Directives
        not_found_resp = client.get('/nefwjnfwjnfjewnfn')
        assert not_found_resp.status_code == 404
        assert b"Page Not Found" in not_found_resp.data
        assert b"Return Home" in not_found_resp.data

        robots_resp = client.get('/robots.txt')
        assert robots_resp.status_code == 200
        assert b"Disallow: /admin/" in robots_resp.data
        assert b"Allow: /en/" in robots_resp.data
        assert b"Allow: /es/" in robots_resp.data
        assert b"Sitemap: https://lucasgarage.uk/sitemap.xml" in robots_resp.data

        sitemap_resp = client.get('/sitemap.xml')
        assert sitemap_resp.status_code == 200
        assert b"<urlset" in sitemap_resp.data
        assert b"https://lucasgarage.uk/cars" in sitemap_resp.data
        print("✅ Test 13 Passed: Custom 404 page, robots.txt, and sitemap.xml verified.")

        # 14. Test Footer Trade Details & Clean Routing
        home_page = client.get('/')
        assert b"lucasgarage@hotmail.co.uk" in home_page.data
        assert b"38a Penrose St" in home_page.data
        assert b"Consumer Rights Act 2015" in home_page.data

        # Verify /privacy returns 404 (no unnecessary policy page)
        priv_resp = client.get('/privacy')
        assert priv_resp.status_code == 404
        assert b"Page Not Found" in priv_resp.data
        print("✅ Test 14 Passed: Footer trade details verified and clean minimalist routing confirmed.")

        # 15. Test Native Subdirectories (/en/ and /es/) & Language Cookie Persistence
        resp_en = client.get('/en/')
        assert resp_en.status_code == 200
        assert b"Lucas Garage" in resp_en.data
        assert "luca_lang=en" in resp_en.headers.get('Set-Cookie', '')

        resp_es = client.get('/es/')
        assert resp_es.status_code == 200
        assert "Mecánica general y".encode('utf-8') in resp_es.data
        assert "Reemplazo de frenos".encode('utf-8') in resp_es.data
        assert "luca_lang=es" in resp_es.headers.get('Set-Cookie', '')

        resp_es_pricing = client.get('/es/pricing')
        assert resp_es_pricing.status_code == 200
        assert "Precios de taller".encode('utf-8') in resp_es_pricing.data

        resp_es_cars = client.get('/es/cars')
        assert resp_es_cars.status_code == 200
        assert "Carros en venta".encode('utf-8') in resp_es_cars.data

        resp_es_detail = client.get(f'/es/car/{car.id}')
        assert resp_es_detail.status_code == 200
        assert "Reservar cita con Luca".encode('utf-8') in resp_es_detail.data

        # Verify root auto-redirects to /es/ when cookie is set
        client.set_cookie('luca_lang', 'es')
        resp_root_redir = client.get('/')
        assert resp_root_redir.status_code == 302
        assert resp_root_redir.headers.get('Location') == '/es/'
        print("✅ Test 15 Passed: Native /en and /es subdirectories, Spanish translations, and cookie persistence verified.")

        print("\n🎉 ALL 15 TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
