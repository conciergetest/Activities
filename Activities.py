import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import time
import base64
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DB_FILE = "aquatic_bookings.db"
ACTIVITY = "Kayak Tour & Snorkeling"
SHIFTS = ["9:00 AM", "11:00 AM", "2:00 PM"]
KAYAK_MAX = 12
SNORKEL_MAX = 8
KAYAK_TYPES = ["Type ①", "Type ②"]

# Snorkeling only on specific day+shift combinations
# weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
SNORKEL_SCHEDULE = {
    "9:00 AM":  [1, 3, 5],   # Tue, Thu, Sat
    "11:00 AM": [],           # No snorkeling
    "2:00 PM":  [0, 2, 4, 6], # Mon, Wed, Fri, Sun
}

def snorkel_allowed(day_date: date, shift: str) -> bool:
    return day_date.weekday() in SNORKEL_SCHEDULE.get(shift, [])

# ─── SPLASH SCREEN ────────────────────────────────────────────────────────────
def get_base64_of_image(image_path):
    """Convert image to base64 string"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

def show_splash_screen():
    """Display splash screen with Waldorf Astoria logo for 15 seconds"""
    
    # Check if splash has already been shown
    if 'splash_shown' not in st.session_state:
        st.session_state.splash_shown = False
    
    if st.session_state.splash_shown:
        return
    
    # Try to load the local image
    image_path = Path("LOGO.png")
    img_base64 = get_base64_of_image(image_path)
    
    # If local image not found, use a placeholder or you can paste a base64 string here
    if img_base64:
        img_src = f"data:image/png;base64,{img_base64}"
    else:
        # Fallback: you can replace this with your own base64 string or URL
        img_src = None
    
    # Splash screen HTML/CSS - 15 seconds duration
    splash_html = f"""
    <style>
    #splash-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #001f3f 0%, #003d7a 50%, #0074D9 100%);
        z-index: 999999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        animation: fadeOut 1s ease-in-out 14.5s forwards;
    }}
    
    #splash-overlay img {{
        max-width: 80%;
        max-height: 70vh;
        border-radius: 12px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        animation: scaleIn 1s ease-out;
    }}
    
    #splash-overlay .splash-text {{
        color: white;
        font-family: 'Georgia', serif;
        text-align: center;
        margin-top: 20px;
        animation: slideUp 1s ease-out 0.5s both;
    }}
    
    #splash-overlay .splash-text h1 {{
        font-size: 2.5rem;
        font-weight: 300;
        letter-spacing: 4px;
        margin-bottom: 10px;
        text-transform: uppercase;
    }}
    
    #splash-overlay .splash-text p {{
        font-size: 1.1rem;
        opacity: 0.8;
        letter-spacing: 2px;
    }}
    
    #splash-overlay .loading-bar {{
        width: 200px;
        height: 3px;
        background: rgba(255,255,255,0.2);
        border-radius: 3px;
        margin-top: 30px;
        overflow: hidden;
    }}
    
    #splash-overlay .loading-bar::after {{
        content: '';
        display: block;
        width: 0%;
        height: 100%;
        background: #D4AF37;
        animation: loading 14s ease-in-out forwards;
    }}
    
    @keyframes fadeOut {{
        to {{
            opacity: 0;
            visibility: hidden;
        }}
    }}
    
    @keyframes scaleIn {{
        from {{
            transform: scale(0.8);
            opacity: 0;
        }}
        to {{
            transform: scale(1);
            opacity: 1;
        }}
    }}
    
    @keyframes slideUp {{
        from {{
            transform: translateY(30px);
            opacity: 0;
        }}
        to {{
            transform: translateY(0);
            opacity: 1;
        }}
    }}
    
    @keyframes loading {{
        to {{
            width: 100%;
        }}
    }}
    
    .main-content {{
        animation: fadeIn 1s ease-in-out 14.5s both;
    }}
    
    @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}
    </style>
    
    <div id="splash-overlay">
        {f'<img src="{img_src}" alt="Waldorf Astoria Costa Rica">' if img_src else ''}
        <div class="splash-text">
            <h1>Waldorf Astoria</h1>
            <p>Costa Rica</p>
            <div style="font-size: 0.9rem; margin-top: 15px; opacity: 0.6;">
                RESERVACIONES KAYAK & SNORKELING
            </div>
        </div>
        <div class="loading-bar"></div>
    </div>
    """
    
    st.markdown(splash_html, unsafe_allow_html=True)
    st.session_state.splash_shown = True
    
    # 15 seconds delay to let the animation play
    time.sleep(15)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                day_date   TEXT NOT NULL,
                shift      TEXT NOT NULL,
                type       TEXT NOT NULL,  -- 'kayak' or 'snorkel'
                guest_name TEXT NOT NULL,
                room       TEXT,
                pax        INTEGER NOT NULL DEFAULT 1,
                kayak_type TEXT              -- only for kayak
            )
        """)
        # Migration: if core columns are missing, recreate the table
        existing = [r[1] for r in conn.execute("PRAGMA table_info(bookings)").fetchall()]
        required = {"week_start", "day_date", "shift", "type", "guest_name", "pax"}
        if not required.issubset(set(existing)):
            conn.execute("DROP TABLE IF EXISTS bookings")
            conn.execute("""
                CREATE TABLE bookings (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start TEXT NOT NULL,
                    day_date   TEXT NOT NULL,
                    shift      TEXT NOT NULL,
                    type       TEXT NOT NULL,
                    guest_name TEXT NOT NULL,
                    room       TEXT,
                    pax        INTEGER NOT NULL DEFAULT 1,
                    kayak_type TEXT
                )
            """)
        else:
            # Add any individually missing optional columns
            if "kayak_type" not in existing:
                conn.execute("ALTER TABLE bookings ADD COLUMN kayak_type TEXT")

def load_week(week_start: date):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM bookings WHERE week_start = ? ORDER BY day_date, shift, type, id",
            (str(week_start),)
        ).fetchall()
    return [dict(r) for r in rows]

def add_booking(week_start, day_date, shift, btype, guest_name, room, pax, kayak_type=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO bookings (week_start,day_date,shift,type,guest_name,room,pax,kayak_type) VALUES (?,?,?,?,?,?,?,?)",
            (str(week_start), str(day_date), shift, btype, guest_name, room, pax, kayak_type)
        )

def update_booking(bid, guest_name, room, pax, kayak_type=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE bookings SET guest_name=?, room=?, pax=?, kayak_type=? WHERE id=?",
            (guest_name, room, pax, kayak_type, bid)
        )

def delete_booking(bid):
    with get_conn() as conn:
        conn.execute("DELETE FROM bookings WHERE id=?", (bid,))

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def week_start_from_offset(offset: int) -> date:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(weeks=offset)

def week_days(week_start: date):
    return [week_start + timedelta(days=i) for i in range(7)]

def capacity_bar(used, cap):
    pct = min(used / cap, 1.0)
    if pct < 0.75:
        color = "#2ecc71"
    elif pct < 1.0:
        color = "#f39c12"
    else:
        color = "#e74c3c"
    bar = f"""
    <div style="background:#333;border-radius:4px;height:8px;margin:2px 0 4px 0;">
      <div style="background:{color};width:{pct*100:.0f}%;height:100%;border-radius:4px;"></div>
    </div>"""
    icon = "✅" if used < cap else ("⚠️" if used == cap else "🚫")
    return bar, icon

# ─── SESSION STATE ────────────────────────────────────────────────────────────
def ss_init():
    defaults = {
        "week_offset": 0,
        "form_open": False,
        "form_mode": None,       # 'add_kayak', 'add_snorkel', 'edit'
        "form_ctx": {},          # day_date, shift, type, booking_id
        "refresh": 0,
        "splash_shown": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ─── FORM MODAL ───────────────────────────────────────────────────────────────
def render_form(week_start, all_bookings):
    ctx = st.session_state.form_ctx
    mode = st.session_state.form_mode
    day_date = ctx.get("day_date")
    shift = ctx.get("shift")
    btype = ctx.get("type")
    bid = ctx.get("booking_id")

    is_edit = mode == "edit"
    existing = next((b for b in all_bookings if b["id"] == bid), {}) if is_edit else {}

    day_bookings = [b for b in all_bookings if b["day_date"] == str(day_date) and b["shift"] == shift]
    kayak_pax = sum(b["pax"] for b in day_bookings if b["type"] == "kayak")
    snorkel_pax = sum(b["pax"] for b in day_bookings if b["type"] == "snorkel")
    if is_edit:
        if existing.get("type") == "kayak":
            kayak_pax -= existing.get("pax", 0)
        else:
            snorkel_pax -= existing.get("pax", 0)

    max_pax = KAYAK_MAX - kayak_pax if btype == "kayak" else SNORKEL_MAX - snorkel_pax
    title = ("✏️ Editar" if is_edit else "➕ Agregar") + (" Kayak" if btype == "kayak" else " Snorkeling")
    day_label = day_date.strftime("%A %b %d") if day_date else ""

    st.markdown(f"### {title} — {day_label} · {shift}")
    with st.form("booking_form", clear_on_submit=True):
        guest = st.text_input("Nombre del huésped", value=existing.get("guest_name", ""))
        room = st.text_input("Habitación", value=existing.get("room", "") or "")
        pax = st.number_input("PAX", min_value=1, max_value=max(1, max_pax), value=min(existing.get("pax", 1), max(1, max_pax)))
        ktype = None
        if btype == "kayak":
            ktype = st.selectbox("Tipo", KAYAK_TYPES,
                                  index=KAYAK_TYPES.index(existing["kayak_type"]) if existing.get("kayak_type") in KAYAK_TYPES else 0)
        col1, col2 = st.columns(2)
        submitted = col1.form_submit_button("💾 Guardar")
        cancelled = col2.form_submit_button("❌ Cancelar")

    if submitted:
        if not guest.strip():
            st.error("El nombre del huésped es requerido.")
        elif pax > max_pax:
            st.error(f"No hay cupo suficiente. Disponible: {max_pax} PAX.")
        else:
            if is_edit:
                update_booking(bid, guest.strip(), room.strip() or None, pax, ktype)
            else:
                add_booking(week_start, day_date, shift, btype, guest.strip(), room.strip() or None, pax, ktype)
            st.session_state.form_open = False
            st.session_state.refresh += 1
            st.rerun()
    if cancelled:
        st.session_state.form_open = False
        st.rerun()

# ─── CELL RENDERER ────────────────────────────────────────────────────────────
def render_cell(day_date: date, shift: str, bookings: list):
    day_bookings = [b for b in bookings if b["day_date"] == str(day_date) and b["shift"] == shift]
    kayak_list = [b for b in day_bookings if b["type"] == "kayak"]
    snorkel_list = [b for b in day_bookings if b["type"] == "snorkel"]
    kayak_pax = sum(b["pax"] for b in kayak_list)
    snorkel_pax = sum(b["pax"] for b in snorkel_list)

    # ── KAYAK section ──
    k_bar, k_icon = capacity_bar(kayak_pax, KAYAK_MAX)
    st.markdown(f"**🚣 Kayak** {k_icon} `{kayak_pax}/{KAYAK_MAX}`")
    st.markdown(k_bar, unsafe_allow_html=True)
    for b in kayak_list:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"<small>👤 {b['guest_name']} · Rm {b['room'] or '-'} · {b['pax']} PAX · {b['kayak_type'] or ''}</small>", unsafe_allow_html=True)
        with c2:
            ec, dc = st.columns(2)
            if ec.button("✏️", key=f"e_{b['id']}", help="Editar"):
                st.session_state.form_open = True
                st.session_state.form_mode = "edit"
                st.session_state.form_ctx = {"day_date": day_date, "shift": shift, "type": "kayak", "booking_id": b["id"]}
                st.rerun()
            if dc.button("🗑️", key=f"d_{b['id']}", help="Borrar"):
                delete_booking(b["id"])
                st.session_state.refresh += 1
                st.rerun()
    if st.button("＋🚣", key=f"ak_{day_date}_{shift}", help="Agregar Kayak"):
        st.session_state.form_open = True
        st.session_state.form_mode = "add_kayak"
        st.session_state.form_ctx = {"day_date": day_date, "shift": shift, "type": "kayak"}
        st.rerun()

    # ── SNORKELING section (only if scheduled) ──
    if snorkel_allowed(day_date, shift):
        st.markdown("---")
        s_bar, s_icon = capacity_bar(snorkel_pax, SNORKEL_MAX)
        st.markdown(f"**🤿 Snorkeling** {s_icon} `{snorkel_pax}/{SNORKEL_MAX}`")
        st.markdown(s_bar, unsafe_allow_html=True)
        for b in snorkel_list:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"<small>👤 {b['guest_name']} · Rm {b['room'] or '-'} · {b['pax']} PAX</small>", unsafe_allow_html=True)
            with c2:
                ec, dc = st.columns(2)
                if ec.button("✏️", key=f"e_{b['id']}", help="Editar"):
                    st.session_state.form_open = True
                    st.session_state.form_mode = "edit"
                    st.session_state.form_ctx = {"day_date": day_date, "shift": shift, "type": "snorkel", "booking_id": b["id"]}
                    st.rerun()
                if dc.button("🗑️", key=f"d_{b['id']}", help="Borrar"):
                    delete_booking(b["id"])
                    st.session_state.refresh += 1
                    st.rerun()
        if st.button("＋🤿", key=f"as_{day_date}_{shift}", help="Agregar Snorkeling"):
            st.session_state.form_open = True
            st.session_state.form_mode = "add_snorkel"
            st.session_state.form_ctx = {"day_date": day_date, "shift": shift, "type": "snorkel"}
            st.rerun()

# ─── SUMMARY TABLE ────────────────────────────────────────────────────────────
def render_summary(week_days_list, bookings):
    st.markdown("---")
    st.subheader("📋 Resumen semanal")
    rows = []
    for shift in SHIFTS:
        for d in week_days_list:
            day_b = [b for b in bookings if b["day_date"] == str(d) and b["shift"] == shift]
            kayak_pax = sum(b["pax"] for b in day_b if b["type"] == "kayak")
            snorkel_pax = sum(b["pax"] for b in day_b if b["type"] == "snorkel")
            snorkel_cell = f"{snorkel_pax}/{SNORKEL_MAX}" if snorkel_allowed(d, shift) else "—"
            _, ki = capacity_bar(kayak_pax, KAYAK_MAX)
            _, si = capacity_bar(snorkel_pax, SNORKEL_MAX) if snorkel_allowed(d, shift) else ("", "—")
            rows.append({
                "Turno": shift,
                "Día": d.strftime("%a %b %d"),
                "Kayak": f"{ki} {kayak_pax}/{KAYAK_MAX}",
                "Snorkeling": f"{si} {snorkel_cell}" if snorkel_allowed(d, shift) else "—",
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Aquatic Reservations", page_icon="🌊", layout="wide")
    
    # Initialize session state first
    ss_init()
    
    # Show splash screen before anything else
    show_splash_screen()
    
    init_db()

    week_start = week_start_from_offset(st.session_state.week_offset)
    days = week_days(week_start)
    week_end = days[-1]

    # ── Header ──
    st.title("🌊 Aquatic Reservations")
    st.markdown(f"### {ACTIVITY}")

    # ── Week navigation ──
    nav1, nav2, nav3, nav4 = st.columns([1, 2, 1, 1])
    if nav1.button("◀ Anterior"):
        st.session_state.week_offset -= 1
        st.session_state.form_open = False
        st.rerun()
    nav2.markdown(f"**{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}**", unsafe_allow_html=False)
    if nav3.button("Siguiente ▶"):
        st.session_state.week_offset += 1
        st.session_state.form_open = False
        st.rerun()
    if nav4.button("📅 Semana actual"):
        st.session_state.week_offset = 0
        st.session_state.form_open = False
        st.rerun()

    # ── Load data ──
    bookings = load_week(week_start)

    # ── Form overlay ──
    if st.session_state.form_open:
        render_form(week_start, bookings)
        st.stop()

    # ── Snorkeling schedule legend ──
    with st.expander("ℹ️ Horarios de Snorkeling"):
        st.markdown("""
| Turno | Días con Snorkeling |
|-------|---------------------|
| 9:00 AM | Martes · Jueves · Sábado |
| 11:00 AM | *(solo Kayak)* |
| 2:00 PM | Lunes · Miércoles · Viernes · Domingo |
        """)

    # ── Tabs by shift ──
    tabs = st.tabs([f"🕘 {s}" for s in SHIFTS])
    for tab, shift in zip(tabs, SHIFTS):
        with tab:
            cols = st.columns(7)
            for col, day in zip(cols, days):
                with col:
                    st.markdown(f"**{day.strftime('%a')}**  \n{day.strftime('%b %d')}")
                    st.markdown("---")
                    render_cell(day, shift, bookings)

    # ── Summary ──
    render_summary(days, bookings)

if __name__ == "__main__":
    main()
