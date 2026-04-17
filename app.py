import streamlit as st

st.set_page_config(page_title="Wong Pro Dashboard", layout="wide")

# --- СТИЛІЗАЦІЯ (Повертаємо "чистий" вигляд) ---
st.markdown("""
<style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .panel-card { padding: 20px; border-radius: 15px; margin-bottom: 20px; background-color: white; border: 1px solid #e0e0e0; }
    .status-ok { border-left: 8px solid #2ecc71; }
    .status-err { border-left: 8px solid #ff4b4b; }
    .status-warn { border-left: 8px solid #f1c40f; }
</style>
""", unsafe_allow_input_html=True)

st.title("🌿 Баланс Акваріума + Калькулятор Самомісів")

# --- 1. БЛОК ВВОДУ ТЕСТІВ (Як було раніше) ---
with st.container():
    st.subheader("📋 Поточні тести води")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        base_no3 = st.slider("NO3 (Нітрати)", 0.0, 50.0, 10.0, 0.5)
        base_po4 = st.slider("PO4 (Фосфати)", 0.0, 5.0, 0.5, 0.05)
    with col_t2:
        base_k = st.slider("K (Калій)", 0.0, 30.0, 10.0, 0.5)
        gh = st.slider("GH (Жорсткість)", 0, 20, 8, 1)
    with col_t3:
        kh = st.slider("KH (Лужність)", 0, 20, 3, 1)
        ph = st.slider("pH (Кислотність)", 5.5, 8.5, 6.5, 0.1)

st.divider()

# --- 2. БЛОК САМОМІСІВ (Г/Л ТА ДОЗУВАННЯ) ---
st.subheader("🧪 Розрахунок дозування самомісів")
tank_vol = st.number_input("Чистий об'єм акваріума, л", value=50, step=1)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("**Азот (N)**")
    conc_n = st.number_input("Концентрація NO3, г/л", value=50.0, key="n_g")
    dose_n = st.number_input("Доза N, мл", value=0.0, step=0.5, key="n_ml")
    # Розрахунок: (мл * (г/л)) / об'єм = мг/л
    added_no3 = (dose_n * conc_n) / tank_vol

with c2:
    st.markdown("**Фосфор (P)**")
    conc_p = st.number_input("Концентрація PO4, г/л", value=5.0, key="p_g")
    dose_p = st.number_input("Доза P, мл", value=0.0, step=0.5, key="p_ml")
    added_po4 = (dose_p * conc_p) / tank_vol

with c3:
    st.markdown("**Калій (K)**")
    conc_k = st.number_input("Концентрація K, г/л", value=20.0, key="k_g")
    dose_k = st.number_input("Доза K, мл", value=0.0, step=0.5, key="k_ml")
    added_k = (dose_k * conc_k) / tank_vol

with c4:
    st.markdown("**Залізо (Fe)**")
    conc_fe = st.number_input("Концентрація Fe, г/л", value=1.0, key="fe_g")
    dose_fe = st.number_input("Доза Fe, мл", value=0.0, step=0.5, key="fe_ml")
    added_fe = (dose_fe * conc_fe) / tank_vol

# --- 3. ПІДСУМКОВІ РОЗРАХУНКИ ---
total_no3 = base_no3 + added_no3
total_po4 = base_po4 + added_po4
total_k = base_k + added_k
co2 = 3 * kh * (10**(7 - ph))
redfield = total_no3 / total_po4 if total_po4 > 0 else 0
k_target = gh * 1.5

# --- 4. ВІЗУАЛІЗАЦІЯ ПАНЕЛЕЙ (Як на скриншоті) ---
st.divider()
st.subheader("📊 Дашборд стану після внесення")

m1, m2, m3 = st.columns(3)
m1.metric("NO3:PO4 RATIO", f"{redfield:.1f}", delta=None)
m2.metric("K:GH OFFSET", f"{total_k - gh:.1f}", delta=f"{added_k:.1f} added")
m3.metric("CO2 mg/l", f"{co2:.1f}")

# ПАНЕЛЬ А
st.markdown(f"""<div class="panel-card {'status-err' if co2 > 40 else 'status-ok' if 20<=co2<=35 else 'status-warn'}">
    <b>ПАНЕЛЬ А: СТАТУС CO2 (pH/KH)</b><br>
    {f"🔴 Критичний надлишок CO2 ({co2:.1f} ppm). Ризик для риб." if co2 > 45 else f"🟢 Оптимально ({co2:.1f} ppm)." if 20<=co2<=35 else f"🟡 Низький рівень ({co2:.1f} ppm)."}
    </div>""", unsafe_allow_input_html=True)

# ПАНЕЛЬ Б
st.markdown(f"""<div class="panel-card {'status-ok' if 15<=redfield<=22 else 'status-warn'}">
    <b>ПАНЕЛЬ Б: ПРОПОРЦІЯ РЕДФІЛДА (NO3/PO4)</b><br>
    Після дозування: {total_no3:.1f} / {total_po4:.2f}. Співвідношення: <b>{redfield:.1f}</b>
    </div>""", unsafe_allow_input_html=True)

# ПАНЕЛЬ В
is_blocked = gh > 8 and total_k < k_target
st.markdown(f"""<div class="panel-card {'status-err' if is_blocked else 'status-ok'}">
    <b>ПАНЕЛЬ В: ТРАНСПОРТ ТА АНТАГОНІЗМ (GH/K)</b><br>
    Поточний K: {total_k:.1f} | Поріг для GH {gh}: {k_target:.1f}. 
    {f"🚫 БЛОКУВАННЯ! Додайте ще Калію." if is_blocked else "💎 Транспорт у нормі."}
    </div>""", unsafe_allow_input_html=True)

# Додаткова метрика для заліза
if added_fe > 0:
    st.info(f"🧬 Додано заліза (Fe): **{added_fe:.2f} мг/л**. Сумарна концентрація залежить від накопичення.")
