import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import date, timedelta
import time
import base64
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ACTIVITY = "Kayak Tour & Snorkeling"
SHIFTS = ["9:00 AM", "11:00 AM", "2:00 PM"]
KAYAK_MAX = 12
SNORKEL_MAX = 8
KAYAK_TYPES = ["Type ①", "Type ②"]

# Inicializa Supabase usando los secrets de Streamlit
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# Snorkeling only on specific day+shift combinations
SNORKEL_SCHEDULE = {
    "9:00 AM":  [1, 3, 5],   # Tue, Thu, Sat
    "11:00 AM": [],          # No snorkeling
    "2:00 PM":  [0, 2, 4, 6], # Mon, Wed, Fri, Sun
}

def snorkel_allowed(day_date: date, shift: str) -> bool:
    return day_date.weekday() in SNORKEL_SCHEDULE.get(shift, [])

# ─── SPLASH SCREEN ────────────────────────────────────────────────────────────
def get_base64_of_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

def show_splash_screen():
    if 'splash_shown' not in st.session_state:
        st.session_state.splash_shown = False
    
    if st.session_state.splash_shown:
        return
    
    image_path = Path("LOGO.png")
    img_base64 = get_base64_of_image(image_path)
    img_src = f"data:image/png;base64,{img_base64}" if img_base64 else None
    
    splash_html = f"""
    <style>
    #splash-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #001f3f 0%, #003d7a 50%, #0074D9 100%); z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; animation: fadeOut 1s ease-in-out 14.5s forwards; }}
    #splash-overlay img {{ max-width: 80%; max-height: 70vh; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); animation: scaleIn 1s ease-out; }}
    #splash-overlay .splash-text {{ color: white; font-family: 'Georgia', serif; text-align: center; margin-top: 20px; animation: slideUp 1s ease-out 0.5s both; }}
    #splash-overlay .loading-bar {{ width: 200px; height: 3px; background: rgba(255,255,255,0.2); border-radius: 3px; margin-top: 30px; overflow: hidden; }}
    #splash-overlay .loading-bar::after {{ content: ''; display: block; width: 0%; height: 100%; background: #D4AF37; animation: loading 14s ease-in-out forwards; }}
    @keyframes fadeOut {{ to {{ opacity: 0; visibility: hidden; }} }}
    @keyframes scaleIn {{ from {{ transform: scale(0.8); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
    @keyframes slideUp {{ from {{ transform: translateY(30px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
    @keyframes loading {{ to {{ width: 100%; }} }}
    </style>
    <div id="splash-overlay">
        {f'<img src="{img_src}" alt="Waldorf Astoria Costa Rica">' if img_src else ''}
        <div class="splash-text">
            <h1>Waldorf Astoria</h1>
            <p>Costa Rica</p>
            <div style="font-size: 0.9rem; margin-top: 15px; opacity: 0.6;">RESERVACIONES KAYAK & SNORKELING</div>
        </div>
        <div class="loading-bar"></div>
    </div>
    """
    st.markdown(splash_html, unsafe_allow_html=True)
    st.session_state.splash_shown = True
    time.sleep(15)

# ─── DATABASE FUNCTIONS (SUPABASE) ────────────────────────────────────────────
def load_week(week_start: date):
    response = supabase.table("bookings").select("*").eq("week_start", str(week_start)).order("day_date,shift,type,id").execute()
    return response.data

def add_booking(week_start, day_date, shift, btype, guest_name, room, pax, kayak_type=None):
    supabase.table("bookings").insert({
        "week_start": str(week_start),
        "day_date": str(day_date),
        "shift": shift,
        "type": btype,
        "guest_name": guest_name,
        "room": room,
        "pax": pax,
        "kayak_type": kayak_type
    }).execute()

def update_booking(bid, guest_name, room, pax, kayak_type=None):
    supabase.table("bookings").update({
        "guest_name": guest_name,
        "room": room,
        "pax": pax,
        "kayak_type": kayak_type
    }).eq("id", bid).execute()

def delete_booking(bid):
    supabase.table("bookings").delete().eq("id", bid).execute()

# ─── HELPERS & SESSION STATE ──────────────────────────────────────────────────
def week_start_from_offset(offset: int) -> date:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(weeks=offset)

def week_days(week_start: date):
    return [week_start + timedelta(days=i) for i in range(7)]

def capacity_bar(used, cap):
    pct = min(used / cap, 1.0)
    color = "#2ecc71" if pct < 0.75 else ("#f39c12" if pct < 1.0 else "#e74c3c")
    bar = f'<div style="background:#333;border-radius:4px;height:8px;margin:2px 0 4px 0;"><div style="background:{color};width:{pct*100:.0f}%;height:100%;border-radius:4px;"></div></div>'
    icon = "✅" if used < cap else ("⚠️" if used == cap else "🚫")
    return bar, icon

def ss_init():
    defaults = {"week_offset": 0, "form_open": False, "form_mode": None, "form_ctx": {}, "refresh": 0, "splash_shown": False}
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

# ─── FORM & RENDERERS (Simplificados para brevedad) ───────────────────────────
# ... (Mantén tus funciones render_form, render_cell y render_summary sin cambios)

def main():
    st.set_page_config(page_title="Aquatic Reservations", page_icon="🌊", layout="wide")
    ss_init()
    show_splash_screen()

    week_start = week_start_from_offset(st.session_state.week_offset)
    days = week_days(week_start)
    week_end = days[-1]

    st.title("🌊 Aquatic Reservations")
    
    # Navegación y lógica principal igual que antes...
    bookings = load_week(week_start)
    # ... resto del código main ...

if __name__ == "__main__":
    main()
