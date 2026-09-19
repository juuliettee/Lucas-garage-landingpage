import os
import json
import requests
from models import Car

GARAGE_INFO = {
    "name": "Luca's Garage",
    "address": "40 Penrose Street, Walworth, London SE17 3DW",
    "phone": "07535 321145",
    "hours": {
        "monday_to_friday": "9:00 AM – 6:00 PM",
        "saturday": "1:00 PM – 6:00 PM",
        "sunday": "Closed"
    },
    "services": "Mechanical repairs, servicing, diagnostics, MOT prep, and certified used vehicle sales.",
    "copart_policy": (
        "All our salvage/Copart sourced vehicles are personally inspected, mechanically repaired to OEM standard, "
        "thoroughly serviced, road-tested, and sold with a 30-day mechanical warranty."
    )
}

def get_active_inventory_summary():
    cars = Car.query.filter(Car.status != 'Sold').all()
    if not cars:
        return "There are currently no vehicles listed for sale."
    
    summary_lines = []
    for c in cars:
        ulez = "ULEZ Exempt" if c.ulez_compliant else "Non-ULEZ"
        miles_str = f"{c.mileage:,}" if c.mileage else "N/A"
        summary_lines.append(
            f"- [ID:{c.id}] {c.year} {c.make_model}: £{c.price:,} | {miles_str} miles | "
            f"{c.TransmissionType} | {c.fuel_type} | {ulez} | MOT: {c.mot_expiry or 'Valid'} | "
            f"Condition/History: {c.copart_category or 'Clean'} | Notes: {c.repair_notes or 'Serviced and road-tested'}"
        )
    return "\n".join(summary_lines)

def build_system_prompt():
    inventory = get_active_inventory_summary()
    return f"""You are the friendly, knowledgeable 24/7 AI Sales Assistant for {GARAGE_INFO['name']}, located at {GARAGE_INFO['address']}.
Your job is to assist prospective car buyers, answer mechanical and specification questions, build trust, and help them book an in-person viewing slot so Luca can show them the vehicle.

Garage Details:
- Address: {GARAGE_INFO['address']} (Walworth / Southwark, London)
- Phone: {GARAGE_INFO['phone']}
- Opening Hours: Mon–Fri 9:00 AM – 6:00 PM, Sat 1:00 PM – 6:00 PM, Sun Closed.
- Copart / Salvage Policy: {GARAGE_INFO['copart_policy']}

Current Stock Available in the Garage:
{inventory}

Key Instructions:
1. Always be polite, professional, and clear.
2. If asked about ULEZ, check the car's ULEZ status. Remember London buyers care heavily about this.
3. If asked about Copart, accidents, or repairs, be completely honest, transparent, and reassuring: explain that Luca is an experienced mechanic who directly works on each car, fixes any damage to strict safety standards, gives it a full mechanical inspection and service, and offers viewing/test drives.
4. If the customer wants to see the car, test drive, or visit, encourage them to use the 'Book a Viewing' button or select a time slot on the website during our opening hours.
5. Keep answers direct and concise (2-4 sentences max per response unless technical details are requested).
"""

def generate_ai_response(user_message, conversation_history=None):
    """
    Generates response using Gemini API if GEMINI_API_KEY is available,
    otherwise uses an intelligent local fallback engine.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    system_prompt = build_system_prompt()

    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_message}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 400}
            }
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Gemini API request failed, falling back to local engine: {e}")

    # Intelligent Local Fallback Engine (Zero-API-key mode)
    msg_lower = user_message.lower()
    cars = Car.query.filter(Car.status != 'Sold').all()

    # Question about ULEZ
    if "ulez" in msg_lower:
        matched = [c for c in cars if any(word in c.make_model.lower() for word in msg_lower.split())]
        if matched:
            c = matched[0]
            status = "fully ULEZ compliant and exempt from charges" if c.ulez_compliant else "not ULEZ exempt"
            return f"Yes, the {c.year} {c.make_model} is {status}. Would you like to book an in-person viewing at 40 Penrose Street?"
        else:
            compliant_cars = [f"{c.year} {c.make_model}" for c in cars if c.ulez_compliant]
            if compliant_cars:
                return f"Most of our stock is ULEZ compliant, including: {', '.join(compliant_cars[:3])}. Let me know which vehicle you'd like to view!"
            return "Please check the vehicle listing details or click 'Book a Viewing' to see it in person at 40 Penrose Street."

    # Question about Copart / Damage / Repairs
    if any(k in msg_lower for k in ["copart", "damage", "accident", "cat s", "cat n", "category", "repaired", "salvage"]):
        matched = [c for c in cars if any(word in c.make_model.lower() for word in msg_lower.split())]
        if matched:
            c = matched[0]
            return (
                f"For the {c.year} {c.make_model}, the provenance is recorded as {c.copart_category or 'Clean'}. "
                f"Notes: {c.repair_notes or 'Fully inspected and serviced'}. Luca inspects and repairs all vehicles "
                f"to strict safety standards and road-tests them thoroughly. You are welcome to test drive it!"
            )
        return (
            f"Luca is a professional mechanic with his own workshop at 40 Penrose Street. "
            f"Any Copart-sourced vehicles are meticulously repaired, fully serviced, MOT-checked, and sold with warranty. "
            f"You are welcome to inspect and test drive any car before deciding!"
        )

    # Question about viewing / visiting / opening hours / location
    if any(k in msg_lower for k in ["view", "see", "visit", "test drive", "open", "address", "where", "hours", "saturday"]):
        return (
            f"We are located at {GARAGE_INFO['address']}. Opening hours: Mon–Fri 9:00 AM – 6:00 PM, "
            f"Sat 1:00 PM – 6:00 PM. You can click 'Book a Viewing' on any vehicle listing to reserve a 30-minute slot "
            f"so Luca is ready for you!"
        )

    # Question about price or payment
    if any(k in msg_lower for k in ["price", "discount", "cash", "offer", "finance", "how much"]):
        return (
            "Our vehicles are priced competitively based on their mechanical condition and market value. "
            "We accept bank transfer and card payments. For final offers or trade-ins, you can speak directly with Luca during an in-person viewing."
        )

    # General / Stock Inquiry
    if cars:
        car_titles = [f"{c.year} {c.make_model} (£{c.price:,})" for c in cars[:3]]
        return (
            f"Hello! At Luca's Garage (40 Penrose St, SE17), our current stock includes: {', '.join(car_titles)}. "
            f"All cars are inspected and road-tested by our mechanics. You can ask me about ULEZ, mileage, repairs, or book a viewing slot anytime!"
        )

    return (
        f"Hello from Luca's Garage (40 Penrose St, London SE17 3DW). How can I help you with our vehicles or workshop services today?"
    )
