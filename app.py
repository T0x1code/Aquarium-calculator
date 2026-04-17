import streamlit as st

# 1. Налаштування сторінки
st.set_page_config(page_title="Wong Pro Dashboard", layout="wide")

st.title("🌿 Баланс Акваріума + Самоміси")
st.info("Методологія Dennis Wong")

# --- 1. БЛОК ТЕСТІВ ВОДИ ---
st.header("📋 1. Поточні тести води")
col_t1, col_t2, col_t3 = st.columns(3)

with col_t1:
    base_no3 = st.slider("Тест NO3 (мг/л)", 0.0, 50.0, 10.0, 0.5)
    base_po4 = st.slider("Тест PO4 (мг/л)", 0.0, 5.0, 0.5, 0.05)
with col_t2:
    base_k = st.slider("Тест K (мг/л)", 0.0, 30.0, 10.0, 0.5)
    gh = st.slider("GH (Загальна жорсткість)", 0, 25, 8, 1)
with col_t3:
    kh = st.slider("KH (Карбонатна жорсткість)", 0, 20, 3, 1)
    ph = st.slider("pH (Кислотність)", 5.5, 8.5, 6.5, 0.1)

st.divider()

# --- 2. БЛОК САМОМІСІВ ---
st.header("🧪 2. Дозування добрив (г/л)")
tank_vol = st.number_input("Чистий об'єм акваріума, л", value=50, step=1)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("**Азот (NO3)**")
    # Твій рецепт Нітрату: Са(NO3)2 та Mg(NO3)2
    conc_n = st.number_input("Концентрація, г/л", value=50.0, key="c_n")
    dose_n = st.number_input("Доза, мл", value=0.0, step=0.1, key="d_n")
    added_no3 = (dose_n * conc_n) / tank_vol

with c2:
    st.markdown("**Фосфор (PO4)**")
    conc_p = st.number_input("Концентрація, г/л", value=5.0, key="c_p")
    dose_p = st.number_input("Доза, мл", value=0.0, step=0.1, key="d_p")
    added_po4 = (dose_p * conc_p) / tank_vol

with c3:
    st.markdown("**Калій (K)**")
    conc_k = st.number_input("Концентрація, г/л", value=20.0, key="c_k")
    dose_k = st.number_input("Доза, мл", value=0.0, step=0.1, key="d_k")
    added_k = (dose_k * conc_k) / tank_vol

with c4:
    st.markdown("**Залізо (Fe)**")
    # Твій рецепт Мікро v2.2 (Fe EDTA)
    conc_fe = st.number_input("Концентрація, г/л", value=1.0, key="c_fe")
    dose_fe = st.number_input("Доза, мл", value=0.0, step=0.1, key="d_fe")
    added_fe = (dose_fe * conc_fe) / tank_vol

# --- 3. ПІДСУМКОВІ РОЗРАХУНКИ ---
total_no3 = base_no3 + added_no3
total_po4 = base_po4 + added_po4
total_k = base_k + added_k
co2 = 3 * kh * (10**(7 - ph))
redfield = total_no3 / total_po4 if total_po4 > 0 else 0
k_target = gh * 1.5

st.divider()

# --- 4. ВІЗУАЛІЗАЦІЯ РЕЗУЛЬТАТІВ ---
st.header("📊 3. Прогноз стану після внесення")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Підсумковий NO3", f"{total_no3:.1f}", f"+{added_no3:.1f}")
m2.metric("Підсумковий PO4", f"{total_po4:.2f}", f"+{added_po4:.2f}")
m3.metric("K:GH Offset", f"{total_k - gh:.1f}", f"+{added_k:.1f} K")
m4.metric("CO2 мг/л", f"{co2:.1f}")

st.subheader("Аналіз системи")

# CO2 Аналіз
if co2 > 45:
    st.error(f"🔴 ПАНЕЛЬ А (CO2): Критичний надлишок ({co2:.1f} ppm).")
elif 20 <= co2 <= 35:
    st.success(f"🟢 ПАНЕЛЬ А (CO2): Оптимально ({co2:.1f} ppm).")
else:
    st.warning(f"🟡 ПАНЕЛЬ А (CO2): Низький рів
