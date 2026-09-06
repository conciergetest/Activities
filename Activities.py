import streamlit as st
from supabase import create_client
import pandas as pd
import base64
import os
from datetime import date, timedelta
import streamlit.components.v1 as components

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ACTIVITY = "Kayak Tour & Snorkeling"
SHIFTS = ["9:00 AM", "11:00 AM", "2:00 PM"]
KAYAK_MAX = 12
SNORKEL_MAX = 8
KAYAK_TYPES = ["Type ①", "Type ②"]

SNORKEL_SCHEDULE = {
    "9:00 AM":  [1, 3, 5],
    "11:00 AM": [],
    "2:00 PM":  [0, 2, 4, 6],
}

def snorkel_allowed(day_date: date, shift: str) -> bool:
    return day_date.weekday() in SNORKEL_SCHEDULE.get(shift, [])

# ─── SUPABASE ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def load_week(week_start: date):
    sb = get_supabase()
    res = sb.table("bookings").select("*")\
        .eq("week_start", str(week_start))\
        .order("day_date").order("shift").order("type").order("id")\
        .execute()
    return res.data or []

def add_booking(week_start, day_date, shift, btype, guest_name, room, pax, kayak_type=None):
    get_supabase().table("bookings").insert({
        "week_start": str(week_start), "day_date": str(day_date),
        "shift": shift, "type": btype, "guest_name": guest_name,
        "room": room, "pax": pax, "kayak_type": kayak_type,
    }).execute()

def update_booking(bid, guest_name, room, pax, kayak_type=None):
    get_supabase().table("bookings").update({
        "guest_name": guest_name, "room": room,
        "pax": pax, "kayak_type": kayak_type,
    }).eq("id", bid).execute()

def delete_booking(bid):
    get_supabase().table("bookings").delete().eq("id", bid).execute()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def week_start_from_offset(offset: int) -> date:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(weeks=offset)

def week_days(week_start: date):
    return [week_start + timedelta(days=i) for i in range(7)]

def capacity_bar(used, cap):
    pct = min(used / cap, 1.0)
    color = "#2ecc71" if pct < 0.75 else ("#f39c12" if pct < 1.0 else "#e74c3c")
    bar = (
        f'<div style="background:#333;border-radius:4px;height:8px;margin:2px 0 4px 0;">'
        f'<div style="background:{color};width:{pct*100:.0f}%;height:100%;border-radius:4px;"></div></div>'
    )
    icon = "✅" if used < cap else ("⚠️" if used == cap else "🚫")
    return bar, icon

def shift_sort_key(shift: str) -> int:
    return SHIFTS.index(shift) if shift in SHIFTS else 99

# ─── SESSION STATE ────────────────────────────────────────────────────────────
def ss_init():
    defaults = {
        "week_offset": 0, "form_open": False,
        "form_mode": None, "form_ctx": {}, "refresh": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ─── SPLASH SCREEN (fondo azul marino con nubes) ────────────────────────────
def render_splash():
    import time
    splash_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOGO.png")
    if not os.path.exists(splash_path):
        return

    with open(splash_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    st.markdown("""
    <style>
    #MainMenu, header, footer { visibility: hidden !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    .block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

    DURATION = 6.0
    st.markdown(f"""
    <style>
    .splash-wrap {{
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: 2147483647;
        /* ── FONDO AZUL MARINO CON NUBES ── */
        background:
            radial-gradient(ellipse at 15% 25%, rgba(255,255,255,0.18) 0%, transparent 45%),
            radial-gradient(ellipse at 85% 15%, rgba(255,255,255,0.12) 0%, transparent 40%),
            radial-gradient(ellipse at 50% 75%, rgba(255,255,255,0.15) 0%, transparent 50%),
            radial-gradient(ellipse at 30% 60%, rgba(255,255,255,0.08) 0%, transparent 35%),
            radial-gradient(ellipse at 70% 45%, rgba(255,255,255,0.1) 0%, transparent 42%),
            linear-gradient(180deg, #0c2a4a 0%, #164e7a 25%, #1e6a9e 50%, #2d8ab8 75%, #4aa8d8 100%);
        background-position: center;
        background-size: cover;
        background-repeat: no-repeat;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        align-items: center;
        padding-bottom: 48px;
        box-sizing: border-box;
        animation: splashFadeIn 0.8s ease;
    }}
    @keyframes splashFadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}

    /* ── LOGO COMO CAPA INDEPENDIENTE ── */
    .splash-logo {{
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background-image: url("data:image/png;base64,{img_b64}");
        background-position: center;
        background-size: contain;
        background-repeat: no-repeat;
        z-index: 1;
        pointer-events: none;
    }}

    .splash-bar-track {{
        position: relative;
        z-index: 2;
        width: 220px;
        height: 4px;
        background: rgba(255,255,255,0.25);
        border-radius: 4px;
        overflow: hidden;
    }}
    .splash-bar-fill {{
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, #B8860B, #FFD700, #B8860B);
        border-radius: 4px;
        animation: barGrow {DURATION:.1f}s ease-in-out forwards;
    }}
    @keyframes barGrow {{ from {{ width:0%; }} to {{ width:100%; }} }}
    </style>

    <div class="splash-wrap">
        <div class="splash-logo"></div>
        <div class="splash-bar-track">
            <div class="splash-bar-fill"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    time.sleep(DURATION)
    st.session_state.splash_done = True
    st.rerun()

# ─── DASHBOARD (sin gráfico) ─────────────────────────────────────────────────
def render_dashboard(bookings, days):
    today_str = str(date.today())
    today_bookings = [b for b in bookings if b["day_date"] == today_str]
    today_kayak = sum(b["pax"] for b in today_bookings if b["type"] == "kayak")
    today_snorkel = sum(b["pax"] for b in today_bookings if b["type"] == "snorkel")
    total_week = len(bookings)
    total_pax = sum(b["pax"] for b in bookings)

    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📅 Reservas hoy", len(today_bookings), delta=None)
    k2.metric("🚣 Kayak hoy", f"{today_kayak}/{KAYAK_MAX}", delta=None)
    k3.metric("🤿 Snorkel hoy", f"{today_snorkel}/{SNORKEL_MAX}", delta=None)
    k4.metric("📊 Total semana", f"{total_week} reservas · {total_pax} PAX", delta=None)

    alerts = []
    for d in days:
        for shift in SHIFTS:
            day_b = [b for b in bookings if b["day_date"] == str(d) and b["shift"] == shift]
            kayak_pax = sum(b["pax"] for b in day_b if b["type"] == "kayak")
            snorkel_pax = sum(b["pax"] for b in day_b if b["type"] == "snorkel")
            day_label = d.strftime("%a %b %d")

            if kayak_pax >= KAYAK_MAX:
                alerts.append(("🔴", f"Kayak LLENO — {day_label} · {shift}"))
            elif kayak_pax >= KAYAK_MAX * 0.75:
                alerts.append(("🟡", f"Kayak casi lleno ({kayak_pax}/{KAYAK_MAX}) — {day_label} · {shift}"))

            if snorkel_allowed(d, shift):
                if snorkel_pax >= SNORKEL_MAX:
                    alerts.append(("🔴", f"Snorkeling LLENO — {day_label} · {shift}"))
                elif snorkel_pax >= SNORKEL_MAX * 0.75:
                    alerts.append(("🟡", f"Snorkeling casi lleno ({snorkel_pax}/{SNORKEL_MAX}) — {day_label} · {shift}"))

    if alerts:
        st.markdown("#### ⚠️ Alertas de cupo")
        cols = st.columns(min(3, len(alerts)))
        for i, (icon, msg) in enumerate(alerts[:6]):
            with cols[i % len(cols)]:
                st.warning(f"{icon} {msg}")

    if today_bookings:
        st.markdown("#### 📌 Reservas de hoy")
        today_bookings.sort(key=lambda b: (shift_sort_key(b["shift"]), b["type"], b["guest_name"]))
        rows = []
        for b in today_bookings:
            rows.append({
                "Turno": b["shift"],
                "Tipo": "🚣 Kayak" if b["type"] == "kayak" else "🤿 Snorkel",
                "Huésped": b["guest_name"],
                "Hab.": b["room"] or "—",
                "PAX": b["pax"],
                "Kayak": b.get("kayak_type") or "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("📭 No hay reservas para hoy.")

    st.markdown("---")

# ─── FORM ─────────────────────────────────────────────────────────────────────
def render_form(week_start, all_bookings):
    ctx = st.session_state.form_ctx
    mode = st.session_state.form_mode
    day_date = ctx.get("day_date")
    shift = ctx.get("shift")
    btype = ctx.get("type")
    bid = ctx.get("booking_id")
    is_edit = mode == "edit"
    existing = next((b for b in all_bookings if b["id"] == bid), {}) if is_edit else {}

    day_b = [b for b in all_bookings if b["day_date"] == str(day_date) and b["shift"] == shift]
    kayak_pax = sum(b["pax"] for b in day_b if b["type"] == "kayak")
    snorkel_pax = sum(b["pax"] for b in day_b if b["type"] == "snorkel")
    if is_edit:
        if existing.get("type") == "kayak":
            kayak_pax -= existing.get("pax", 0)
        else:
            snorkel_pax -= existing.get("pax", 0)

    max_pax = KAYAK_MAX - kayak_pax if btype == "kayak" else SNORKEL_MAX - snorkel_pax
    title_str = ("✏️ Editar" if is_edit else "➕ Agregar") + (" Kayak" if btype == "kayak" else " Snorkeling")
    day_label = day_date.strftime("%A %b %d") if day_date else ""

    st.markdown(f"### {title_str} — {day_label} · {shift}")
    with st.form("booking_form", clear_on_submit=True):
        guest = st.text_input("Nombre del huésped", value=existing.get("guest_name", ""))
        room = st.text_input("Habitación", value=existing.get("room", "") or "")
        pax = st.number_input("PAX", min_value=1, max_value=max(1, max_pax),
                              value=min(existing.get("pax", 1), max(1, max_pax)))
        ktype = None
        if btype == "kayak":
            ktype = st.selectbox("Tipo", KAYAK_TYPES,
                index=KAYAK_TYPES.index(existing["kayak_type"]) if existing.get("kayak_type") in KAYAK_TYPES else 0)
        c1, c2 = st.columns(2)
        submitted = c1.form_submit_button("💾 Guardar")
        cancelled = c2.form_submit_button("❌ Cancelar")

    if submitted:
        if not guest.strip():
            st.error("El nombre del huésped es requerido.")
        elif pax > max_pax:
            st.error(f"No hay cupo. Disponible: {max_pax} PAX.")
        else:
            if is_edit:
                update_booking(bid, guest.strip(), room.strip() or None, pax, ktype)
            else:
                add_booking(week_start, day_date, shift, btype,
                            guest.strip(), room.strip() or None, pax, ktype)
            st.session_state.form_open = False
            st.session_state.refresh += 1
            st.rerun()
    if cancelled:
        st.session_state.form_open = False
        st.rerun()

# ─── CELL ─────────────────────────────────────────────────────────────────────
def render_cell(day_date: date, shift: str, bookings: list):
    day_b = [b for b in bookings if b["day_date"] == str(day_date) and b["shift"] == shift]
    kayak_list = [b for b in day_b if b["type"] == "kayak"]
    snorkel_list = [b for b in day_b if b["type"] == "snorkel"]
    kayak_pax = sum(b["pax"] for b in kayak_list)
    snorkel_pax = sum(b["pax"] for b in snorkel_list)

    k_bar, k_icon = capacity_bar(kayak_pax, KAYAK_MAX)
    st.markdown(f"**🚣 Kayak** {k_icon} `{kayak_pax}/{KAYAK_MAX}`")
    st.markdown(k_bar, unsafe_allow_html=True)
    for b in kayak_list:
        c1, c2 = st.columns([4, 1])
        c1.markdown(
            f"<small>👤 {b['guest_name']} · Rm {b['room'] or '-'} · "
            f"{b['pax']} PAX · {b.get('kayak_type') or ''}</small>",
            unsafe_allow_html=True)
        with c2:
            ec, dc = st.columns(2)
            if ec.button("Edit", key=f"e_{b['id']}", help="Editar reserva"):
                st.session_state.form_open = True
                st.session_state.form_mode = "edit"
                st.session_state.form_ctx = {"day_date": day_date, "shift": shift,
                                              "type": "kayak", "booking_id": b["id"]}
                st.rerun()
            if dc.button("Del", key=f"d_{b['id']}", help="Borrar reserva"):
                delete_booking(b["id"])
                st.session_state.refresh += 1
                st.rerun()
    if st.button("＋🚣", key=f"ak_{day_date}_{shift}", help="Agregar Kayak"):
        st.session_state.form_open = True
        st.session_state.form_mode = "add_kayak"
        st.session_state.form_ctx = {"day_date": day_date, "shift": shift, "type": "kayak"}
        st.rerun()

    if snorkel_allowed(day_date, shift):
        st.markdown("---")
        s_bar, s_icon = capacity_bar(snorkel_pax, SNORKEL_MAX)
        st.markdown(f"**🤿 Snorkeling** {s_icon} `{snorkel_pax}/{SNORKEL_MAX}`")
        st.markdown(s_bar, unsafe_allow_html=True)
        for b in snorkel_list:
            c1, c2 = st.columns([4, 1])
            c1.markdown(
                f"<small>👤 {b['guest_name']} · Rm {b['room'] or '-'} · {b['pax']} PAX</small>",
                unsafe_allow_html=True)
            with c2:
                ec, dc = st.columns(2)
                if ec.button("Edit", key=f"e_{b['id']}", help="Editar reserva"):
                    st.session_state.form_open = True
                    st.session_state.form_mode = "edit"
                    st.session_state.form_ctx = {"day_date": day_date, "shift": shift,
                                                  "type": "snorkel", "booking_id": b["id"]}
                    st.rerun()
                if dc.button("Del", key=f"d_{b['id']}", help="Borrar reserva"):
                    delete_booking(b["id"])
                    st.session_state.refresh += 1
                    st.rerun()
        if st.button("＋🤿", key=f"as_{day_date}_{shift}", help="Agregar Snorkeling"):
            st.session_state.form_open = True
            st.session_state.form_mode = "add_snorkel"
            st.session_state.form_ctx = {"day_date": day_date, "shift": shift, "type": "snorkel"}
            st.rerun()

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
def render_summary(week_days_list, bookings):
    st.markdown("---")
    st.subheader("📋 Resumen semanal")
    rows = []
    for shift in SHIFTS:
        for d in week_days_list:
            day_b = [b for b in bookings if b["day_date"] == str(d) and b["shift"] == shift]
            kayak_pax = sum(b["pax"] for b in day_b if b["type"] == "kayak")
            snorkel_pax = sum(b["pax"] for b in day_b if b["type"] == "snorkel")
            _, ki = capacity_bar(kayak_pax, KAYAK_MAX)
            if snorkel_allowed(d, shift):
                _, si = capacity_bar(snorkel_pax, SNORKEL_MAX)
                snorkel_cell = f"{si} {snorkel_pax}/{SNORKEL_MAX}"
            else:
                snorkel_cell = "—"
            rows.append({
                "Turno": shift, "Día": d.strftime("%a %b %d"),
                "Kayak": f"{ki} {kayak_pax}/{KAYAK_MAX}",
                "Snorkeling": snorkel_cell,
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Aquatic Reservations", page_icon="🌊", layout="wide")
    ss_init()

    if not st.session_state.get("splash_done"):
        render_splash()

    week_start = week_start_from_offset(st.session_state.week_offset)
    days = week_days(week_start)
    week_end = days[-1]

    # ── CSS MODO OSCURO ──
    st.markdown("""
    <style>
    html, body, [class*="css-"] {
        background-color: #0e1117 !important;
        color: #f0f2f6 !important;
    }
    .stApp {
        background-color: #0e1117 !important;
    }
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.5rem !important;
    }
    h1 {
        margin-top: 0.3rem !important;
        margin-bottom: 0.2rem !important;
        line-height: 1.3 !important;
        color: #f0f2f6 !important;
    }
    h2, h3, h4, h5, h6 {
        color: #f0f2f6 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #00FFFF !important;
        text-shadow: 0 0 8px rgba(0,255,255,0.3);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #cccccc !important;
    }
    [data-testid="stMetric"] {
        background: #161b22 !important;
        border-radius: 10px !important;
        padding: 12px !important;
        border: 1px solid #21262d !important;
    }
    input, textarea, select, .stDateInput > div > div {
        background-color: #161b22 !important;
        color: #f0f2f6 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
    }
    .stDateInput > div > div:focus-within {
        border-color: #00FFFF !important;
        box-shadow: 0 0 0 1px #00FFFF !important;
    }
    button[kind="secondary"] {
        background-color: #21262d !important;
        color: #f0f2f6 !important;
        border: 1px solid #30363d !important;
    }
    button[kind="secondary"]:hover {
        background-color: #30363d !important;
        border-color: #00FFFF !important;
    }
    button[kind="primary"] {
        background-color: #00FFFF !important;
        color: #0e1117 !important;
        border: none !important;
        font-weight: 700 !important;
    }
    button[kind="primary"]:hover {
        background-color: #33FFFF !important;
    }
    button[data-baseweb="tab"] {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        padding: 10px 24px !important;
        letter-spacing: 0.02em;
        color: #8b949e !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #00FFFF !important;
        border-bottom-color: #00FFFF !important;
    }
    .stDataFrame, [data-testid="stDataFrameResizable"] {
        background-color: #161b22 !important;
    }
    .stDataFrame th {
        background-color: #21262d !important;
        color: #00FFFF !important;
        font-weight: 700 !important;
    }
    .stDataFrame td {
        background-color: #161b22 !important;
        color: #f0f2f6 !important;
        border-bottom: 1px solid #21262d !important;
    }
    details {
        background-color: #161b22 !important;
        border: 1px solid #21262d !important;
        border-radius: 8px !important;
    }
    summary {
        color: #f0f2f6 !important;
        font-weight: 600 !important;
    }
    .stAlert {
        background-color: #161b22 !important;
        border-left-color: #f39c12 !important;
    }
    .stAlert p {
        color: #f0f2f6 !important;
    }
    [data-testid="stForm"] {
        background-color: #161b22 !important;
        border: 1px solid #21262d !important;
        border-radius: 10px !important;
        padding: 16px !important;
    }
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0e1117; }
    ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #00FFFF; }
    </style>
    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER CON LogoWayne.png AL LADO DEL TÍTULO
    # ═══════════════════════════════════════════════════════════════════════════
    head_left, head_right = st.columns([5, 2])

    with head_left:
        logo_col, text_col = st.columns([1, 5])
        with logo_col:
            try:
                st.image("LogoWayne.png", width=75)
            except Exception:
                st.markdown("🌊")
        with text_col:
            st.markdown(
                "<div style='display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:0.5rem;'>"
                "<h1 style='margin:0 !important; line-height:1.3 !important; color:#f0f2f6 !important; font-size:2.25rem;'>Aquatic Reservations</h1>"
                "<h3 style='margin:0 !important; line-height:1.3 !important; color:#f0f2f6 !important; font-size:1.17rem; opacity:0.85;'>"
                "Kayak Tour & Snorkeling | Hecho por Fred Wayne (Concierge)"
                "</h3>"
                "</div>",
                unsafe_allow_html=True
            )
            today = date.today()
            meses_es = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }
            fecha_str = f"{meses_es[today.month]} {today.day}, {today.year}"
            st.markdown(
                f"<div style='color:#00FFFF; font-size:1.1rem; font-weight:700; "
                f"text-shadow: 0 0 8px rgba(0,255,255,0.4); margin-bottom:0.5rem;'>"
                f"📅 {fecha_str}"
                f"</div>",
                unsafe_allow_html=True
            )

    with head_right:
        components.html("""
        <style>
        #aquatic-clock {
            color: #00FFFF;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-align: right;
            line-height: 1.25;
            text-shadow: 0 0 12px rgba(0,255,255,0.55);
            padding-top: 6px;
        }
        #aquatic-clock .clk-date {
            font-size: 0.82rem;
            opacity: 0.92;
            font-weight: 600;
        }
        #aquatic-clock .clk-time {
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: 0.06em;
        }
        </style>
        <div id="aquatic-clock">
            <div class="clk-date" id="ac-date"></div>
            <div class="clk-time" id="ac-time"></div>
        </div>
        <script>
        (function(){
            function pad(n){ return n<10 ? '0'+n : n; }
            var days = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
            var months = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
            function update(){
                var now = new Date();
                var dStr = days[now.getDay()] + ', ' + now.getDate() + ' ' + months[now.getMonth()] + ' ' + now.getFullYear();
                var tStr = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
                var elD = document.getElementById('ac-date');
                var elT = document.getElementById('ac-time');
                if(elD) elD.textContent = dStr;
                if(elT) elT.textContent = tStr;
            }
            setInterval(update, 1000);
            update();
        })();
        </script>
        """, height=65)

    # ═══════════════════════════════════════════════════════════════════════════
    # NAVEGACIÓN DE SEMANA
    # ═══════════════════════════════════════════════════════════════════════════
    n1, n2, n3, n4 = st.columns([1, 2, 1, 1])
    if n1.button("◀ Anterior"):
        st.session_state.week_offset -= 1
        st.session_state.form_open = False
        st.rerun()

    n2.markdown(
        f"<div style='color:#00FFFF; font-size:1.5rem; font-weight:800; text-align:center; "
        f"text-shadow: 0 0 10px rgba(0,255,255,0.5); letter-spacing:0.02em;'>"
        f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
        f"</div>",
        unsafe_allow_html=True
    )

    if n3.button("Siguiente ▶"):
        st.session_state.week_offset += 1
        st.session_state.form_open = False
        st.rerun()
    if n4.button("📅 Semana actual"):
        st.session_state.week_offset = 0
        st.session_state.form_open = False
        st.rerun()

    # ── Almanaque ──
    cal1, cal2, cal3 = st.columns([1, 2, 5])
    cal1.markdown("**🗓️ Ir a fecha:**")
    picked = cal2.date_input("Ir a fecha", value=week_start,
                             label_visibility="collapsed", key="date_jumper")
    if picked:
        today_monday = date.today() - timedelta(days=date.today().weekday())
        picked_monday = picked - timedelta(days=picked.weekday())
        new_offset = round((picked_monday - today_monday).days / 7)
        if new_offset != st.session_state.week_offset:
            st.session_state.week_offset = new_offset
            st.session_state.form_open = False
            st.rerun()

    # ── Cargar datos ──
    bookings = load_week(week_start)

    # ── DASHBOARD ──
    render_dashboard(bookings, days)

    # ── Formulario ──
    if st.session_state.form_open:
        render_form(week_start, bookings)
        st.stop()

    # ── Leyenda snorkeling ──
    with st.expander("ℹ️ Horarios de Snorkeling"):
        st.markdown("""
| Turno | Días con Snorkeling |
|-------|---------------------|
| 9:00 AM  | Martes · Jueves · Sábado |
| 11:00 AM | *(solo Kayak)* |
| 2:00 PM  | Lunes · Miércoles · Viernes · Domingo |
        """)

    # ── Tabs por turno ──
    tabs = st.tabs([f"🕘 {s}" for s in SHIFTS])
    for tab, shift in zip(tabs, SHIFTS):
        with tab:
            cols = st.columns(7)
            for col, day in zip(cols, days):
                with col:
                    st.markdown(f"**{day.strftime('%a')}**  \n{day.strftime('%b %d')}")
                    st.markdown("---")
                    render_cell(day, shift, bookings)

    # ── Resumen ──
    render_summary(days, bookings)

if __name__ == "__main__":
    main()
