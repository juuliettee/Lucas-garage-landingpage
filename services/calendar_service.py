import urllib.parse
from datetime import datetime, timedelta

GARAGE_NAME = "Luca's Garage"
GARAGE_ADDRESS = "40 Penrose Street, Walworth, London SE17 3DW"
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
    title = f"Viewing: {car_name} - Luca's Garage"
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

def generate_ics_content(booking_id, car_name, booking_date, booking_time, customer_name, customer_phone, customer_email, garage_email="luca@lucasgarage.co.uk"):
    """
    Generates standard RFC 5545 iCalendar content with METHOD:REQUEST.
    Both Apple Calendar and Google Calendar/Outlook automatically detect and display 1-tap accept prompts.
    """
    try:
        start_dt = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        start_dt = datetime.utcnow() + timedelta(days=1)

    end_dt = start_dt + timedelta(minutes=45)
    
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dtstart = start_dt.strftime("%Y%m%dT%H%M00")
    dtend = end_dt.strftime("%Y%m%dT%H%M00")
    uid = f"booking-{booking_id}-{start_dt.strftime('%Y%m%d%H%M')}@lucasgarage.co.uk"
    
    description = (
        f"Vehicle Viewing Appointment\\n"
        f"Car: {car_name}\\n"
        f"Customer: {customer_name}\\n"
        f"Contact: {customer_phone}\\n"
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
        f"SUMMARY:Viewing: {car_name} at Luca's Garage",
        f"DESCRIPTION:{description}",
        f"LOCATION:{GARAGE_ADDRESS}",
        f"ORGANIZER;CN=\"Luca's Garage\":mailto:{garage_email}",
        f"ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;CN={customer_name}:mailto:{customer_email}",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "BEGIN:VALARM",
        "TRIGGER:-PT2H",
        "ACTION:DISPLAY",
        "DESCRIPTION:Reminder: Vehicle viewing appointment at Luca's Garage in 2 hours",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(ics_lines)
