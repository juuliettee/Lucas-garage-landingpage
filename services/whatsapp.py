import os
import urllib.parse
import requests

GARAGE_MOBILE = os.getenv("GARAGE_MOBILE", "447535321145") # Luca's UK number formatted with country code
CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY") # Optional: Free personal WhatsApp alert key

def generate_customer_whatsapp_url(car_name=None, message_type="inquiry"):
    """
    Generates a WhatsApp click-to-chat URL so buyers on the site can message Luca directly with one tap.
    """
    if message_type == "inquiry" and car_name:
        text = f"Hi Luca, I saw the {car_name} listed on your website and would like some more details."
    elif message_type == "viewing" and car_name:
        text = f"Hi Luca, I'd like to arrange a viewing for the {car_name} at 38a Penrose Street."
    else:
        text = "Hi Luca, I have an inquiry about vehicle servicing / cars for sale at Lucas Garage."

    encoded_text = urllib.parse.quote(text)
    return f"https://wa.me/{GARAGE_MOBILE}?text={encoded_text}"

def generate_viewing_request_whatsapp_url(car_name, booking_date=None, booking_time=None, customer_name=None, customer_note=None):
    """
    Generates a direct WhatsApp link to Luca with the user's preferred date and time pre-filled.
    """
    greeting = f"Hi Luca, I would like to book a viewing for the {car_name} at Lucas Garage (38a Penrose Street)."
    details = []
    if booking_date:
        clean_date = booking_date
        if "-" in booking_date:
            parts = booking_date.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                clean_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
        details.append(f"Date: {clean_date}")
    if booking_time:
        details.append(f"Time: {booking_time}")
    if customer_name:
        details.append(f"Name: {customer_name}")
    if customer_note:
        details.append(f"Note: {customer_note}")

    if details:
        details_str = "\n".join(details)
        text = f"{greeting}\n\n{details_str}\n\nIs this viewing slot available?"
    else:
        text = f"{greeting}\n\nIs this car available for a viewing?"

    encoded_text = urllib.parse.quote(text)
    return f"https://wa.me/{GARAGE_MOBILE}?text={encoded_text}"

def generate_luca_reply_whatsapp_url(customer_phone, car_name, booking_date, booking_time):
    """
    Generates a 1-tap WhatsApp reply URL for Luca to confirm or message the customer.
    """
    # Clean phone number
    clean_phone = customer_phone.replace(" ", "").replace("-", "")
    if clean_phone.startswith("0"):
        clean_phone = "44" + clean_phone[1:]
    
    text = (
        f"Hi! Luca here from Lucas Garage (38a Penrose St). "
        f"Confirming your viewing for the {car_name} on {booking_date} at {booking_time}. "
        f"See you then! Let me know if you need any directions."
    )
    encoded_text = urllib.parse.quote(text)
    return f"https://wa.me/{clean_phone}?text={encoded_text}"

def send_whatsapp_booking_alert(booking, car):
    """
    Sends an automated WhatsApp alert to Luca's phone when a buyer books a viewing slot.
    Uses CallMeBot free personal WhatsApp API if CALLMEBOT_API_KEY is configured,
    or logs the dispatch cleanly for audit.
    """
    alert_message = (
        f"*NEW CAR VIEWING BOOKED!*\n\n"
        f"- *Vehicle:* {car.make_model} ({car.year})\n"
        f"- *Price:* £{car.price:,}\n"
        f"- *Customer:* {booking.customer_name}\n"
        f"- *Phone:* {booking.customer_phone}\n"
        f"- *Date:* {booking.booking_date}\n"
        f"- *Time Slot:* {booking.booking_time}\n"
        f"- *Location:* 38a Penrose St, SE17 3DW\n"
    )
    if booking.notes:
        alert_message += f"- *Notes:* {booking.notes}\n"

    try:
        print("\n" + "="*50)
        print("WHATSAPP NOTIFICATION TO LUCA:")
        print(alert_message)
        print("="*50 + "\n")
    except Exception:
        # Fallback for Windows console encodings like cp1252 that don't support emojis
        safe_message = alert_message.encode('ascii', errors='replace').decode('ascii')
        print("\n" + "="*50)
        print("WHATSAPP NOTIFICATION TO LUCA:")
        print(safe_message)
        print("="*50 + "\n")

    if CALLMEBOT_API_KEY:
        try:
            encoded_msg = urllib.parse.quote(alert_message)
            url = f"https://api.callmebot.com/whatsapp.php?phone=+{GARAGE_MOBILE}&text={encoded_msg}&apikey={CALLMEBOT_API_KEY}"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Error dispatching WhatsApp message via CallMeBot: {e}")
            return False

    return True
