import urllib.parse
from datetime import datetime, timedelta

GARAGE_NAME = "Lucas Garage"
GARAGE_ADDRESS = "38a Penrose Street, Walworth, London SE17 3DW"
GARAGE_PHONE = "07535 321145"

def create_google_calendar_url(car_name, booking_date, booking_time, customer_name, customer_phone):
    """
    Creates a 1-tap Google Calendar web link for instant event creation.
    """
    try:
        start_dt = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "https://calendar.google.com"

    end_dt = start_dt + timedelta(minutes=45)
    
    dates_param = f"{start_dt.strftime('%Y%m%dT%H%M00')}/{end_dt.strftime('%Y%m%dT%H%M00')}"
    title = f"Viewing: {car_name} - Lucas Garage"
    details = (
        f"Vehicle Viewing Appointment\n\n"
        f"Vehicle: {car_name}\n"
        f"Customer: {customer_name}\n"
        f"Phone: {customer_phone}\n\n"
        f"Location: {GARAGE_ADDRESS}\n"
        f"Direct Phone / WhatsApp: {GARAGE_PHONE}"
    )
    
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates_param,
        "details": details,
        "location": GARAGE_ADDRESS
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"

def clean_ics_text(val):
    """Strips CRLF and escapes delimiter characters to prevent iCalendar injection."""
    if not val:
        return ""
    cleaned = str(val).replace("\r", "").replace("\n", " ").strip()
    return cleaned.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")

def generate_ics_content(booking_id, car_name, booking_date, booking_time, customer_name, customer_phone, customer_email, garage_email="luca@lucasgarage.co.uk"):
    """
    Generates standard RFC 5545 iCalendar content with METHOD:REQUEST.
    Both Apple Calendar and Google Calendar/Outlook automatically detect and display 1-tap accept prompts.
    """
    clean_date = str(booking_date).replace("\r", "").replace("\n", "").strip()
    clean_time = str(booking_time).replace("\r", "").replace("\n", "").strip()
    try:
        start_dt = datetime.strptime(f"{clean_date} {clean_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        start_dt = datetime.utcnow() + timedelta(days=1)

    end_dt = start_dt + timedelta(minutes=45)
    
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dtstart = start_dt.strftime("%Y%m%dT%H%M00")
    dtend = end_dt.strftime("%Y%m%dT%H%M00")
    uid = f"booking-{booking_id}-{start_dt.strftime('%Y%m%d%H%M')}@lucasgarage.co.uk"
    
    safe_car = clean_ics_text(car_name)
    safe_cust_name = clean_ics_text(customer_name)
    safe_cust_phone = clean_ics_text(customer_phone)
    safe_cust_email = str(customer_email or "").replace("\r", "").replace("\n", "").strip()

    description = (
        f"Vehicle Viewing Appointment\\n"
        f"Car: {safe_car}\\n"
        f"Customer: {safe_cust_name}\\n"
        f"Contact: {safe_cust_phone}\\n"
        f"Location: {GARAGE_ADDRESS}\\n"
        f"Workshop Mobile: {GARAGE_PHONE}"
    )
    
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Lucas Garage//Viewing Scheduler//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:Viewing: {safe_car} at Lucas Garage",
        f"DESCRIPTION:{description}",
        f"LOCATION:{GARAGE_ADDRESS}",
        f"ORGANIZER;CN=\"Lucas Garage\":mailto:{garage_email}",
        f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN={safe_cust_name}:mailto:{safe_cust_email}",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "BEGIN:VALARM",
        "TRIGGER:-PT2H",
        "ACTION:DISPLAY",
        "DESCRIPTION:Reminder: Vehicle viewing appointment at Lucas Garage in 2 hours",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(ics_lines)
