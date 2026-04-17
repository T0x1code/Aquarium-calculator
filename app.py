import streamlit as st

# Налаштування сторінки
st.set_page_config(page_title="Wong Aquarium Dashboard", layout="wide")

# Кастомний CSS для "дорогого" вигляду
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .panel-card {
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        margin-bottom: 20px;
        background-color: white;
    }
    .status-critical { border-left: 8px solid #ff4b4b; }
    .status-ok { border-left: 8px solid #2ecc71; }
    .status-warning { border-left: 8px solid #f1c40f; }
    </style>
    """, unsafe_allow_input_html=True)

st.title("🌿 Баланс Акваріума (Dennis Wong)")

# --- Секція Вводу (Компактна) ---
with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        no3 = st.slider("NO3 (Нітрати)", 0.0, 50.0, 20.0, step=0.5)
        po4 = st.slider("PO4 (Фосфати)", 0.0, 5.0, 1.0, step=0.05)
    with col2:
        k = st.slider("K (Калій)", 0.0, 30.0, 9.0, step=0.5)
        gh = st.slider("GH (Жорсткість)", 0, 20, 10)
    with col3:
        kh = st.slider("KH (Лужність)", 0, 20, 4)
        ph = st.slider("pH (Кислотність)", 5.5, 8.5, 6.0, step=0.1)

# --- Розрахунки ---
co2 = 3 * kh * (10**(7 - ph))
redfield = no3 / po4 if po4 > 0 else 0
k_offset = k - gh

# --- Шапка з Метриками ---
m1, m2, m3 = st.columns(3)
m1.metric("NO3:PO4 RATIO", f"{redfield:.1f}")
m2.metric("K:GH OFFSET", f"{k_offset:.1f}")
m3.metric("CO2 EST.", "High" if co2 > 35 else "Optimal" if co2 > 20 else "Low")

st.divider()

# --- ПАНЕЛЬ А: CO2 ---
status_a = "status-critical" if co2 > 45 else "status-ok" if 20 <= co2 <= 35 else "status-warning"
st.markdown(f"""
    <div class="panel-card {status_a}">
        <h3>ПАНЕЛЬ А: СТАТУС CO2 (pH/KH)</h3>
        <p style="font-size: 1.2rem;">
            {f"🔴 <b>Критичний надлишок CO2 ({co2:.1f} ppm)</b>. Ризик для гідробіонтів." if co2 > 45 
            else f"🟢 <b>Оптимально ({co2:.1f} ppm)</b>. Золотий стандарт Денніса Вонга." if 20 <= co2 <= 35 
            else f"🟡 <b>Низький рівень ({co2:.1f} ppm)</b>. Можлива стагнація росту."}
        </p>
    </div>
    """, unsafe_allow_input_html=True)

# --- ПАНЕЛЬ Б: РЕДФІЛД ---
status_b = "status-ok" if 15 <= redfield <= 22 else "status-warning"
st.markdown(f"""
    <div class="panel-card {status_b}">
        <h3>ПАНЕЛЬ Б: ПРОПОРЦІЯ РЕДФІЛДА (NO3/PO4)</h3>
        <p style="font-size: 1.2rem;">
            {f"✅ <b>Золота зона (Rich Dosing)</b> — Оптимально для форсованого травника." if 15 <= redfield <= 22 
            else "⚠️ <b>Дисбаланс</b>. Перевірте дозування макро-елементів."}
        </p>
    </div>
    """, unsafe_allow_input_html=True)

# --- ПАНЕЛЬ В: АНТАГОНІЗМ ---
k_target = gh * 1.5
is_blocked = gh > 8 and k < k_target
status_c = "status-critical" if is_blocked else "status-ok"
st.markdown(f"""
    <div class="panel-card {status_c}">
        <h3>ПАНЕЛЬ В: ТРАНСПОРТ ТА АНТАГОНІЗМ (GH/K)</h3>
        <p style="font-size: 1.2rem;">
            {f"🚫 <b>Високий GH блокує нітрати</b>. Підніміть K мінімум до {k_target:.1f} мг/л." if is_blocked 
            else "💎 <b>Оптимальний баланс</b>. Калій успішно конкурує з кальцієм/магнієм."}
        </p>
    </div>
    """, unsafe_allow_input_html=True)
