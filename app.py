import streamlit as st

# 1. Налаштування сторінки без важких стилів
st.set_page_config(page_title="Wong Pro Dashboard", layout="wide")

st.title("🌿 Баланс Акваріума + Самоміси")
st.markdown("Методологія Денніса Вонга")

# --- 1. БЛОК ВВОДУ ТЕСТІВ ---
st.header("📋 1. Поточні параметри (Тести)")
col_t1, col_t2, col_t3 = st.columns(3)

with col_t1:
    base_no3 = st.slider("NO3 (Нітрати), мг/л", 0.0, 50.0, 10.0, 0.5)
    base_po4 = st.slider("PO4 (Фосфати), мг/л", 0.0, 5.0, 0.5, 0.05)
with col_t2:
    base_k = st.slider("K (Калій), мг/л", 0.0, 30.0, 10.0, 0.5)
    gh = st.slider("GH (Загальна жорсткість)", 0, 25, 8, 1)
with col_t3:
    kh = st.slider("KH (Карбонатна жорсткість)", 0, 20, 3, 1)
    ph = st.slider("pH (Кислотність)", 5.5, 8.5, 6.5, 0.1)

st.divider()

# --- 2. БЛОК САМОМІСІВ (Розрахунок у г/л) ---
st.header("🧪 2. Дозування самомісів")
tank_vol = st.number_input("Чистий об'єм води в акваріумі, л", value=50, step=1)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.subheader("Азот (N)")
    conc_n = st.number_input("Концентрація NO3, г/л", value=50.0)
    dose_n = st.number_input("Внести N, мл", value=0.0, step=0.1)
    added_no3 = (dose_n * conc_n) / tank_vol

with c2:
    st.subheader("Фосфор (P)")
    conc_p = st.number_input("Концентрація PO4, г/л", value=5.0)
    dose_p = st.number_input("Внести P, мл", value=0.0, step=0.1)
    added_po4 = (dose_p * conc_p) / tank_vol

with c3:
    st.subheader("Калій (K)")
    conc_k = st.number_input("Концентрація K, г/л", value=20.0)
    dose_k = st.number_input("Внести K, мл", value=0.0, step=0.1)
    added_k = (dose_k * conc_k) / tank_vol

with c4:
    st.subheader("Залізо (Fe)")
    conc_fe = st.number_input("Концентрація Fe, г/л", value=1.0)
    dose_fe = st.number_input("Внести Fe, мл", value=0.0, step=0.1)
    added_fe = (dose_fe * conc_fe) / tank_vol

# --- 3. РОЗРАХУНОК ФІНАЛЬНИХ ЗНАЧЕНЬ ---
total_no3 = base_no3 + added_no3
total_po4 = base_po4 + added_po4
total_k = base_k + added_k
co2 = 3 * kh * (10**(7 - ph))
redfield = total_no3 / total_po4 if total_po4 > 0 else 0
k_target = gh * 1.5

st.divider()

# --- 4. ПАНЕЛЬ РЕЗУЛЬТАТІВ ---
st.header("📊 3. Прогноз стану води")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Підсумковий NO3", f"{total_no3:.1f}", f"+{added_no3:.1f}")
m2.metric("Підсумковий PO4", f"{total_po4:.2f}", f"+{added_po4:.2f}")
m3.metric("K:GH Offset", f"{total_k - gh:.1f}", f"+{added_k:.1f} K")
m4.metric("CO2 мг/л", f"{co2:.1f}")

st.markdown("### Аналіз за Dennis Wong:")

# Панель CO2
if co2 > 45:
    st.error(f"🔴 **ПАНЕЛЬ А (CO2):** Критичний надлишок ({co2:.1f} ppm). Ризик для риб!")
elif 20 <= co2 <= 35:
    st.success(f"🟢 **ПАНЕЛЬ А (CO2):** Оптимально ({co2:.1f} ppm).")
else:
    st.warning(f"🟡 **ПАНЕЛЬ А (CO2):** Низький рівень ({co2:.1f} ppm).")

# Панель Редфілда
if 15 <= redfield <= 22:
    st.success(f"✅ **ПАНЕЛЬ Б (Редфілд):** Співвідношення {redfield:.1f} — Ідеальний баланс.")
else:
    st.info(f"📊 **ПАНЕЛЬ Б (Редфілд):** Поточне співвідношення {redfield:.1f}. Ціль: 16-20.")

# Панель K:GH
is_blocked = gh > 8 and total_k < k_target
if is_blocked:
    st.error(f"🚫 **ПАНЕЛЬ В (Транспорт):** Калій {total_k:.1f} замалий для GH {gh}. Нітрати блокуються! Ціль: >{k_target:.1f}")
else:
    st.success(f"💎 **ПАНЕЛЬ В (Транспорт):** Співвідношення K/GH у нормі.")

if added_fe > 0:
    st.info(f"🧬 Додано заліза: {added_fe:.2f} мг/л.")# ПАНЕЛЬ А
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
