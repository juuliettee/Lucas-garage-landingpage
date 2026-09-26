import os
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from services.calendar_service import generate_ics_content, create_google_calendar_url

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "bookings@lucasgarage.co.uk")
LUCA_EMAIL = os.getenv("LUCA_EMAIL", "luca@lucasgarage.co.uk")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_LUCA_CHAT_ID = os.getenv("TELEGRAM_LUCA_CHAT_ID", "")

def send_telegram_alert(booking, car):
    """
    Sends an instant push notification to Luca's phone via a private Telegram bot.
    Free forever, zero rate limits, instant delivery with quick-action buttons.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_LUCA_CHAT_ID:
        return False
    
    clean_phone = booking.customer_phone.replace(" ", "").replace("-", "")
    if clean_phone.startswith("0"):
        clean_phone = "44" + clean_phone[1:]
    
    text = (
        f"🚗 *NEW VERIFIED VIEWING!*\n\n"
        f"• *Vehicle:* {car.year} {car.make_model} (£{car.price:,})\n"
        f"• *Customer:* {booking.customer_name}\n"
        f"• *Phone:* `{booking.customer_phone}`\n"
        f"• *Email:* {booking.customer_email}\n"
        f"• *Slot:* *{booking.booking_date}* at *{booking.booking_time}*\n"
        f"• *Notes:* {booking.notes or 'None'}\n"
    )
    
    payload = {
        "chat_id": TELEGRAM_LUCA_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "💬 WhatsApp Customer", "url": f"https://wa.me/{clean_phone}"},
                    {"text": "📞 Call Customer", "url": f"tel:{clean_phone}"}
                ]
            ]
        }
    }
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json=payload, timeout=8)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram dispatch notice: {e}")
        return False

def send_email(recipient_email, subject, html_body, ics_content=None):
    """
    Sends an email with optional embedded RFC 5545 .ics calendar attachment.
    Supports Resend API (RESEND_API_KEY) or standard SMTP (Gmail/Custom).
    Falls back gracefully to logging if credentials are not yet set.
    """
    # 1. Option A: Resend API (re_...)
    resend_api_key = os.getenv("RESEND_API_KEY")
    if resend_api_key:
        try:
            from_header = os.getenv("FROM_EMAIL") or "Luca's Garage <onboarding@resend.dev>"
            payload = {
                "from": from_header,
                "to": [recipient_email],
                "subject": subject,
                "html": html_body
            }
            if ics_content:
                import base64
                payload["attachments"] = [{
                    "filename": "viewing_invite.ics",
                    "content": base64.b64encode(ics_content.encode("utf-8")).decode("utf-8")
                }]
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=10
            )
            if resp.status_code in [200, 201]:
                return True
            else:
                print(f"[RESEND NOTICE] Resend returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[RESEND ERROR] Failed to send via Resend: {e}")

    # 2. Option B: SMTP (e.g. Gmail with App Password)
    if SMTP_USER and SMTP_PASS:
        try:
            from_address = os.getenv("FROM_EMAIL") or SMTP_USER
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = f"Luca's Garage <{from_address}>"
            msg["To"] = recipient_email

            alt_part = MIMEMultipart("alternative")
            alt_part.attach(MIMEText(html_body, "html"))
            msg.attach(alt_part)

            if ics_content:
                ics_part = MIMEBase("text", "calendar", method="REQUEST", name="viewing_invite.ics")
                ics_part.set_payload(ics_content.encode("utf-8"))
                encoders.encode_base64(ics_part)
                ics_part.add_header("Content-Disposition", "attachment; filename=\"viewing_invite.ics\"")
                ics_part.add_header("Content-Class", "urn:content-classes:calendarmessage")
                msg.attach(ics_part)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(from_address, [recipient_email], msg.as_string())
            return True
        except Exception as e:
            print(f"[SMTP ERROR] SMTP dispatch warning for {recipient_email}: {e}")
            return False

    # 3. Fallback: Log for developer inspection
    print(f"\n[DEV NOTICE] Mail credentials not set in .env. Email to {recipient_email} simulated:")
    print(f"Subject: {subject}")
    print("-" * 50)
    return True

def send_verification_email(customer_email, customer_name, car, booking_date, booking_time, verification_url):
    """
    Sends the 1-click verification email to the customer to eliminate no-shows.
    """
    subject = f"Confirm your viewing: {car.year} {car.make_model} at Luca's Garage"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b1117; margin: 0; padding: 24px; color: #f1f5f9;">
        <div style="max-width: 580px; margin: auto; background-color: #141e28; border-radius: 16px; border: 1px solid #243344; overflow: hidden;">
            <div style="background-color: #070c11; padding: 24px 32px; border-bottom: 1px solid #243344;">
                <h2 style="margin: 0; font-size: 20px; font-weight: 800; color: #f8fafc;">LUCA'S <span style="color: #f59e0b;">GARAGE</span></h2>
                <p style="margin: 4px 0 0; font-size: 12px; color: #94a3b8;">40 Penrose Street, Walworth, London SE17 3DW</p>
            </div>
            <div style="padding: 32px; color: #cbd5e1; line-height: 1.6;">
                <h1 style="color: #f8fafc; font-size: 22px; font-weight: 800; margin: 0 0 12px;">Confirm Your Viewing Appointment</h1>
                <p style="font-size: 14px; margin: 0 0 18px;">Hi {customer_name},</p>
                <p style="font-size: 14px; margin: 0 0 24px;">
                    We have received your viewing request for the <strong>{car.year} {car.make_model}</strong>. 
                    Please tap the button below to confirm your appointment:
                </p>
                
                <div style="text-align: center; margin: 28px 0;">
                    <a href="{verification_url}" style="background-color: #f59e0b; color: #0b1117; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-weight: 800; font-size: 15px; display: inline-block;">
                        &check; Confirm My Viewing Slot
                    </a>
                </div>

                <div style="background-color: #0b1117; border: 1px solid #243344; border-radius: 12px; padding: 18px; margin: 24px 0; font-size: 13px; color: #cbd5e1;">
                    <div style="font-weight: bold; color: #f8fafc; font-size: 15px; margin-bottom: 8px;">{car.year} {car.make_model} - £{car.price:,}</div>
                    <div>&bull; <strong>Date:</strong> {booking_date}</div>
                    <div>&bull; <strong>Time:</strong> {booking_time}</div>
                    <div>&bull; <strong>Location:</strong> 40 Penrose Street, London SE17 3DW</div>
                </div>

                <p style="font-size: 12px; color: #94a3b8; margin-top: 24px;">
                    If you cannot make this time, you can safely ignore this email and the slot will be released.
                </p>
            </div>
            <div style="background-color: #070c11; border-top: 1px solid #243344; padding: 16px 32px; font-size: 12px; color: #64748b; text-align: center;">
                Luca's Garage &bull; Workshop Direct Mobile: 07535 321145
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(customer_email, subject, html_body)

def dispatch_confirmed_booking_notifications(booking, car):
    """
    Dispatches notifications and calendar entries once email verification is completed.
    1. Sends confirmation email with RFC 5545 .ics calendar attachment to Buyer.
    2. Sends alert email with RFC 5545 .ics calendar attachment to Luca.
    3. Sends Telegram push alert to Luca (if configured).
    """
    gcal_url = create_google_calendar_url(
        car.make_model, booking.booking_date, booking.booking_time,
        booking.customer_name, booking.customer_phone
    )
    ics_text = generate_ics_content(
        booking.id, car.make_model, booking.booking_date, booking.booking_time,
        booking.customer_name, booking.customer_phone, booking.customer_email
    )

    # 1. Customer Confirmation Email with Calendar Attachment
    customer_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1117; padding: 24px; color: #f1f5f9;">
        <div style="max-width: 580px; margin: auto; background-color: #141e28; border-radius: 16px; border: 1px solid #243344; overflow: hidden;">
            <div style="background-color: #070c11; padding: 24px 32px; border-bottom: 1px solid #243344;">
                <h2 style="margin: 0; font-size: 20px; font-weight: 800; color: #f8fafc;">LUCA'S <span style="color: #f59e0b;">GARAGE</span></h2>
                <p style="margin: 4px 0 0; font-size: 12px; color: #94a3b8;">40 Penrose Street, Walworth, London SE17 3DW</p>
            </div>
            <div style="padding: 32px; color: #cbd5e1; line-height: 1.6;">
                <div style="display: inline-block; background-color: #064e3b; color: #34d399; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: bold; margin-bottom: 12px; border: 1px solid #059669;">
                    &check; BOOKING CONFIRMED
                </div>
                <h1 style="color: #f8fafc; font-size: 22px; font-weight: 800; margin: 0 0 12px;">We'll see you at the workshop!</h1>
                <p style="font-size: 14px;">Hi {booking.customer_name}, Luca has your viewing appointment locked in for the <strong>{car.year} {car.make_model}</strong>.</p>
                
                <div style="background-color: #0b1117; border: 1px solid #243344; border-radius: 12px; padding: 18px; margin: 20px 0; font-size: 13px; color: #cbd5e1;">
                    <div>&bull; <strong>Booking Ref:</strong> <span style="color: #f59e0b; font-weight: bold;">#LG-{booking.id}</span></div>
                    <div>&bull; <strong>Date:</strong> {booking.booking_date}</div>
                    <div>&bull; <strong>Time:</strong> {booking.booking_time} (Vehicle viewing)</div>
                    <div>&bull; <strong>Address:</strong> 40 Penrose Street, Walworth, SE17 3DW</div>
                    <div>&bull; <strong>Direct Contact:</strong> 07535 321145</div>
                </div>

                <p style="font-size: 14px; margin-bottom: 14px;">The calendar invite is attached to this email. You can also add it to your calendar in 1 tap:</p>
                <div style="margin-bottom: 24px;">
                    <a href="{gcal_url}" style="background-color: #f59e0b; color: #0b1117; text-decoration: none; padding: 12px 20px; border-radius: 8px; font-weight: 800; font-size: 13px; display: inline-block;">
                        Add to Google Calendar
                    </a>
                </div>

                <div style="border-left: 3px solid #f59e0b; padding-left: 12px; font-size: 12px; color: #94a3b8;">
                    <strong>Location note:</strong> Customer parking is available directly outside the workshop on Penrose Street.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    send_email(
        booking.customer_email,
        f"Confirmed: Viewing for {car.make_model} at Luca's Garage",
        customer_html,
        ics_content=ics_text
    )

    # 2. Email Alert to Luca with Calendar Attachment
    luca_html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #0f172a;">New Verified Customer Viewing!</h2>
        <p>A buyer has verified their email and locked in an appointment.</p>
        <div style="background: #f1f5f9; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p><strong>Vehicle:</strong> {car.year} {car.make_model} (£{car.price:,})</p>
            <p><strong>Date & Time:</strong> {booking.booking_date} at {booking.booking_time}</p>
            <p><strong>Customer Name:</strong> {booking.customer_name}</p>
            <p><strong>Phone:</strong> {booking.customer_phone}</p>
            <p><strong>Email:</strong> {booking.customer_email}</p>
            <p><strong>Customer Notes:</strong> {booking.notes or 'None'}</p>
        </div>
        <p><a href="{gcal_url}" style="background: #0284c7; color: white; padding: 10px 16px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Add to Luca's Calendar</a></p>
    </div>
    """
    send_email(
        LUCA_EMAIL,
        f"New Viewing Confirmed: {car.make_model} - {booking.booking_date} {booking.booking_time}",
        luca_html,
        ics_content=ics_text
    )

    # 3. Instant Telegram push alert to Luca's mobile
    send_telegram_alert(booking, car)
