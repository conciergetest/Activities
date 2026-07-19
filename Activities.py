import streamlit as st
from supabase import create_client
import pandas as pd
import base64
import os
from datetime import date, timedelta

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ACTIVITY = "Kayak Tour & Snorkeling | MADE BY FRED WAYNE"
SHIFTS = ["9:00 AM", "11:00 AM", "2:00 PM"]
KAYAK_MAX = 12
SNORKEL_MAX = 8
KAYAK_TYPES = ["Type ①", "Type ②"]

# weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
SNORKEL_SCHEDULE = {
    "9:00 AM":  [1, 3, 5],    # Tue, Thu, Sat
    "11:00 AM": [],            # No snorkeling
    "2:00 PM":  [0, 2, 4, 6], # Mon, Wed, Fri, Sun
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
        "week_start": str(week_start),
        "day_date":   str(day_date),
        "shift":      shift,
        "type":       btype,
        "guest_name": guest_name,
        "room":       room,
        "pax":        pax,
        "kayak_type": kayak_type,
    }).execute()

def update_booking(bid, guest_name, room, pax, kayak_type=None):
    get_supabase().table("bookings").update({
        "guest_name": guest_name,
        "room":       room,
        "pax":        pax,
        "kayak_type": kayak_type,
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
        f'<div style="background:{color};width:{pct*100:.0f}%;height:100%;border-radius:4px;"></div>'
        f'</div>'
    )
    icon = "✅" if used < cap else ("⚠️" if used == cap else "🚫")
    return bar, icon

# ─── SESSION STATE ────────────────────────────────────────────────────────────
def ss_init():
    defaults = {
        "week_offset": 0,
        "form_open":   False,
        "form_mode":   None,
        "form_ctx":    {},
        "refresh":     0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ─── SPLASH SCREEN ────────────────────────────────────────────────────────────
def render_splash():
    """
    Splash a pantalla completa con barra de progreso dorada.
    Usa time.sleep() + st.rerun() — funciona 100% en Streamlit Cloud.
    Sin JavaScript: la barra de progreso es CSS puro.
    Duración: ~4 segundos.
    """
    import time

    # Buscar la imagen
    for candidate in ["LOGO.png", "splash.png"]:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), candidate)
        if os.path.exists(p):
            splash_path = p
            break
    else:
        # No hay imagen; saltamos el splash
        return

    with open(splash_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # Ocultar chrome de Streamlit durante el splash
    st.markdown("""
    <style>
    #MainMenu, header, footer { visibility: hidden !important; }
    section[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    .block-container { padding-top: 0 !important; padding-bottom: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

    # Splash a pantalla completa — imagen de fondo + barra de progreso CSS
    DURATION = 10.0   # segundos visibles
    st.markdown(f"""
    <style>
    .splash-wrap {{
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        z-index: 2147483647;
        background: #87CEEB url("data:image/png;base64,{img_b64}") center/contain no-repeat;
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        align-items: center;
        padding-bottom: 48px;
        box-sizing: border-box;
        animation: splashFadeIn 0.8s ease;
    }}
    @keyframes splashFadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}

    .splash-bar-track {{
        width: 220px;
        height: 4px;
        background: rgba(255,255,255,0.2);
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
        <div class="splash-bar-track">
            <div class="splash-bar-fill"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # El CSS ya anima la barra; el sleep garantiza la duración en el servidor
    time.sleep(DURATION)
    st.session_state.splash_done = True
    st.rerun()

# ─── FORM ─────────────────────────────────────────────────────────────────────
def render_form(week_start, all_bookings):
    ctx      = st.session_state.form_ctx
    mode     = st.session_state.form_mode
    day_date = ctx.get("day_date")
    shift    = ctx.get("shift")
    btype    = ctx.get("type")
    bid      = ctx.get("booking_id")
    is_edit  = mode == "edit"
    existing = next((b for b in all_bookings if b["id"] == bid), {}) if is_edit else {}

    day_b       = [b for b in all_bookings if b["day_date"] == str(day_date) and b["shift"] == shift]
    kayak_pax   = sum(b["pax"] for b in day_b if b["type"] == "kayak")
    snorkel_pax = sum(b["pax"] for b in day_b if b["type"] == "snorkel")
    if is_edit:
        if existing.get("type") == "kayak":   kayak_pax   -= existing.get("pax", 0)
        else:                                  snorkel_pax -= existing.get("pax", 0)

    max_pax   = KAYAK_MAX - kayak_pax if btype == "kayak" else SNORKEL_MAX - snorkel_pax
    title_str = ("✏️ Editar" if is_edit else "➕ Agregar") + (" Kayak" if btype == "kayak" else " Snorkeling")
    day_label = day_date.strftime("%A %b %d") if day_date else ""

    st.markdown(f"### {title_str} — {day_label} · {shift}")
    with st.form("booking_form", clear_on_submit=True):
        guest = st.text_input("Nombre del huésped", value=existing.get("guest_name", ""))
        room  = st.text_input("Habitación",          value=existing.get("room", "") or "")
        pax   = st.number_input("PAX", min_value=1,
                                max_value=max(1, max_pax),
                                value=min(existing.get("pax", 1), max(1, max_pax)))
        ktype = None
        if btype == "kayak":
            ktype = st.selectbox("Tipo", KAYAK_TYPES,
                index=KAYAK_TYPES.index(existing["kayak_type"])
                      if existing.get("kayak_type") in KAYAK_TYPES else 0)
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
            st.session_state.refresh  += 1
            st.rerun()
    if cancelled:
        st.session_state.form_open = False
        st.rerun()

# ─── CELL ─────────────────────────────────────────────────────────────────────
def render_cell(day_date: date, shift: str, bookings: list):
    day_b       = [b for b in bookings if b["day_date"] == str(day_date) and b["shift"] == shift]
    kayak_list  = [b for b in day_b if b["type"] == "kayak"]
    snorkel_list= [b for b in day_b if b["type"] == "snorkel"]
    kayak_pax   = sum(b["pax"] for b in kayak_list)
    snorkel_pax = sum(b["pax"] for b in snorkel_list)

    # ── Kayak ──
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
            if ec.button("✏️", key=f"e_{b['id']}", help="Editar"):
                st.session_state.form_open = True
                st.session_state.form_mode = "edit"
                st.session_state.form_ctx  = {"day_date": day_date, "shift": shift,
                                               "type": "kayak", "booking_id": b["id"]}
                st.rerun()
            if dc.button("🗑️", key=f"d_{b['id']}", help="Borrar"):
                delete_booking(b["id"])
                st.session_state.refresh += 1
                st.rerun()
    if st.button("＋🚣", key=f"ak_{day_date}_{shift}", help="Agregar Kayak"):
        st.session_state.form_open = True
        st.session_state.form_mode = "add_kayak"
        st.session_state.form_ctx  = {"day_date": day_date, "shift": shift, "type": "kayak"}
        st.rerun()

    # ── Snorkeling (solo si aplica) ──
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
                if ec.button("✏️", key=f"e_{b['id']}", help="Editar"):
                    st.session_state.form_open = True
                    st.session_state.form_mode = "edit"
                    st.session_state.form_ctx  = {"day_date": day_date, "shift": shift,
                                                   "type": "snorkel", "booking_id": b["id"]}
                    st.rerun()
                if dc.button("🗑️", key=f"d_{b['id']}", help="Borrar"):
                    delete_booking(b["id"])
                    st.session_state.refresh += 1
                    st.rerun()
        if st.button("＋🤿", key=f"as_{day_date}_{shift}", help="Agregar Snorkeling"):
            st.session_state.form_open = True
            st.session_state.form_mode = "add_snorkel"
            st.session_state.form_ctx  = {"day_date": day_date, "shift": shift, "type": "snorkel"}
            st.rerun()

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
def render_summary(week_days_list, bookings):
    st.markdown("---")
    st.subheader("📋 Resumen semanal")
    rows = []
    for shift in SHIFTS:
        for d in week_days_list:
            day_b       = [b for b in bookings if b["day_date"] == str(d) and b["shift"] == shift]
            kayak_pax   = sum(b["pax"] for b in day_b if b["type"] == "kayak")
            snorkel_pax = sum(b["pax"] for b in day_b if b["type"] == "snorkel")
            _, ki = capacity_bar(kayak_pax, KAYAK_MAX)
            if snorkel_allowed(d, shift):
                _, si = capacity_bar(snorkel_pax, SNORKEL_MAX)
                snorkel_cell = f"{si} {snorkel_pax}/{SNORKEL_MAX}"
            else:
                snorkel_cell = "—"
            rows.append({
                "Turno":      shift,
                "Día":        d.strftime("%a %b %d"),
                "Kayak":      f"{ki} {kayak_pax}/{KAYAK_MAX}",
                "Snorkeling": snorkel_cell,
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Aquatic Reservations", page_icon="🌊", layout="wide")
    ss_init()

    # Splash solo en la primera carga de cada sesión
    # render_splash() maneja splash_done internamente y llama st.rerun()
    if not st.session_state.get("splash_done"):
        render_splash()

    week_start = week_start_from_offset(st.session_state.week_offset)
    days       = week_days(week_start)
    week_end   = days[-1]

    # ── CSS: tabs más grandes ──
    st.markdown("""
    <style>
    button[data-baseweb="tab"] {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        padding: 10px 24px !important;
        letter-spacing: 0.02em;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ──
    st.title("🌊 Aquatic Reservations")
    st.markdown(f"### {ACTIVITY}")

    # ── Navegación de semana ──
    n1, n2, n3, n4 = st.columns([1, 2, 1, 1])
    if n1.button("◀ Anterior"):
        st.session_state.week_offset -= 1
        st.session_state.form_open    = False
        st.rerun()
    n2.markdown(f"**{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}**")
    if n3.button("Siguiente ▶"):
        st.session_state.week_offset += 1
        st.session_state.form_open    = False
        st.rerun()
    if n4.button("📅 Semana actual"):
        st.session_state.week_offset = 0
        st.session_state.form_open   = False
        st.rerun()

    # ── Almanaque: saltar a cualquier semana ──
    cal1, cal2, cal3 = st.columns([1, 2, 5])
    cal1.markdown("**🗓️ Ir a fecha:**")
    picked = cal2.date_input(
        "Ir a fecha",
        value=week_start,
        label_visibility="collapsed",
        key="date_jumper",
    )
    if picked:
        today_monday  = date.today() - timedelta(days=date.today().weekday())
        picked_monday = picked       - timedelta(days=picked.weekday())
        new_offset    = round((picked_monday - today_monday).days / 7)
        if new_offset != st.session_state.week_offset:
            st.session_state.week_offset = new_offset
            st.session_state.form_open   = False
            st.rerun()

    # ── Cargar datos ──
    bookings = load_week(week_start)

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
