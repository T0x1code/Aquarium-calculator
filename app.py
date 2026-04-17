import streamlit as st

# 1. Налаштування сторінки
st.set_page_config(page_title="Toxicode Aquarium System", layout="wide")

st.title("🌿 Toxicode Aquarium System")
st.info("Методологія Toxicode (на основі балансу Dennis Wong)")

# --- 1. ПОТОЧНІ ТЕСТИ (ДО ПІДМІНИ) ---
st.sidebar.header("📋 Поточні тести (в акваріумі)")
tank_vol = st.sidebar.number_input("Об'єм акваріума (нетто), л", value=50)
base_no3 = st.sidebar.slider("Тест NO3 (мг/л)", 0.0, 50.0, 20.0, 0.5)
base_po4 = st.sidebar.slider("Тест PO4 (мг/л)", 0.0, 5.0, 1.0, 0.05)
base_k = st.sidebar.slider("Тест K (мг/л)", 0.0, 30.0, 10.0, 0.5)
gh = st.sidebar.slider("GH (Загальна жорсткість)", 0, 25, 8, 1)
kh = st.sidebar.slider("KH (Карбонатна жорсткість)", 0, 20, 3, 1)
ph = st.sidebar.slider("pH (Кислотність)", 5.5, 8.5, 6.5, 0.1)

# --- 2. БЛОК ПІДМІНИ ВОДИ ---
st.header("💧 1. Підміна води")
col_w1, col_w2, col_w3 = st.columns(3)

with col_w1:
    change_pct = st.number_input("Відсоток підміни, %", 0, 100, 30)
with col_w2:
    water_no3 = st.number_input("NO3 у новій воді, мг/л", value=0.0)
with col_w3:
    water_po4 = st.number_input("PO4 у новій воді, мг/л", value=0.0)

# Розрахунок після підміни (пропорційне змішування)
ratio = change_pct / 100
after_w_no3 = (base_no3 * (1 - ratio)) + (water_no3 * ratio)
after_w_po4 = (base_po4 * (1 - ratio)) + (water_po4 * ratio)

st.write(f"📉 *Після підміни (без добрив): NO3: {after_w_no3:.1f} | PO4: {after_w_po4:.2f}*")

st.divider()

# --- 3. БЛОК САМОМІСІВ (ДОБРИВА) ---
st.header("🧪 2. Дозування добрив (г/л)")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("**Азот (NO3)**")
    conc_n = st.number_input("Концентрація, г/л", value=50.0, key="c_n")
    dose_n = st.number_input("Доза N, мл", value=0.0, step=0.1, key="d_n")
    added_no3 = (dose_n * conc_n) / tank_vol

with c2:
    st.markdown("**Фосфор (PO4)**")
    conc_p = st.number_input("Концентрація, г/л", value=5.0, key="c_p")
    dose_p = st.number_input("Доза P, мл", value=0.0, step=0.1, key="d_p")
    added_po4 = (dose_p * conc_p) / tank_vol

with c3:
    st.markdown("**Калій (K)**")
    conc_k = st.number_input("Концентрація, г/л", value=20.0, key="c_k")
    dose_k = st.number_input("Доза K, мл", value=0.0, step=0.1, key="d_k")
    added_k = (dose_k * conc_k) / tank_vol

with c4:
    st.markdown("**Залізо (Fe)**")
    conc_fe = st.number_input("Концентрація, г/л", value=1.0, key="c_fe")
    dose_fe = st.number_input("Доза Fe, мл", value=0.0, step=0.1, key="d_fe")
    added_fe = (dose_fe * conc_fe) / tank_vol

# --- 4. ФІНАЛЬНІ РОЗРАХУНКОВА ---
total_no3 = after_w_no3 + added_no3
total_po4 = after_w_po4 + added_po4
total_k = base_k + added_k # Калій зазвичай не міряють у водопроводі так часто
co2 = 3 * kh * (10**(7 - ph))
redfield = total_no3 / total_po4 if total_po4 > 0 else 0
k_target = gh * 1.5

st.divider()

# --- 5. РЕЗУЛЬТАТИ ---
st.header("📊 3. Прогноз стану системи")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Фінальний NO3", f"{total_no3:.1f}", f"{total_no3 - base_no3:.1f} від старту")
m2.metric("Фінальний PO4", f"{total_po4:.2f}", f"{total_po4 - base_po4:.2f} від старту")
m3.metric("K:GH Offset", f"{total_k - gh:.1f}", f"+{added_k:.1f} K")
m4.metric("CO2 мг/л", f"{co2:.1f}")

st.subheader("Аналіз Toxicode")

# CO2
if co2 > 45:
    st.error(f"🔴 ПАНЕЛЬ А: Критичний надлишок CO2 ({co2:.1f} ppm).")
elif 20 <= co2 <= 35:
    st.success(f"🟢 ПАНЕЛЬ А: CO2 в нормі ({co2:.1f} ppm).")
else:
    st.warning(f"🟡 ПАНЕЛЬ А: Низький CO2 ({co2:.1f} ppm).")

# Redfield
if 15 <= redfield <= 22:
    st.success(f"✅ ПАНЕЛЬ Б: Співвідношення {redfield:.1f} — Баланс.")
else:
    st.info(f"📊 ПАНЕЛЬ Б: Співвідношення {redfield:.1f}. Ідеал 16-20.")

# K:GH
is_blocked = gh > 8 and total_k < k_target
if is_blocked:
    st.error(f"🚫 ПАНЕЛЬ В: Блокування нітратів! Потрібно K > {k_target:.1f}.")
else:
    st.success("💎 ПАНЕЛЬ В: Транспорт нутрієнтів у нормі.")
