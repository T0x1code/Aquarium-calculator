import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System", layout="wide")

st.title("🌿 Toxicode Aquarium System")
st.info("Розширений калькулятор балансу з прогнозом")

# --- 1. ПАРАМЕТРИ ---
st.header("📏 Загальні параметри")

tank_vol = st.number_input("Об'єм (л, нетто)", value=50.0)

tank_type = st.selectbox(
    "Тип системи",
    ["Low-tech", "High-tech", "Shrimp"]
)

st.divider()

# --- 2. ВХІДНІ ДАНІ ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Поточні значення")
    base_no3 = st.number_input("NO3", value=20.0)
    base_po4 = st.number_input("PO4", value=1.0)
    base_k = st.number_input("K", value=10.0)
    gh = st.number_input("GH", value=8.0)
    kh = st.number_input("KH", value=3.0)
    ph = st.number_input("pH", value=6.5)

with col2:
    st.subheader("💧 Підміна")
    change_liters = st.number_input("Обʼєм підміни (л)", value=15.0)
    water_no3 = st.number_input("NO3 нової води", value=0.0)
    water_po4 = st.number_input("PO4 нової води", value=0.0)
    water_k = st.number_input("K нової води", value=0.0)

change_pct = change_liters / tank_vol if tank_vol > 0 else 0

after_w_no3 = base_no3 * (1 - change_pct) + water_no3 * change_pct
after_w_po4 = base_po4 * (1 - change_pct) + water_po4 * change_pct
after_w_k = base_k * (1 - change_pct) + water_k * change_pct

st.write(f"Підміна: {change_pct*100:.1f}%")

st.divider()

# --- 3. ДОЗУВАННЯ ---
st.header("🧪 Добрива")

c1, c2, c3, c4 = st.columns(4)

with c1:
    conc_n = st.number_input("NO3 (г/л)", value=50.0)
    dose_n = st.number_input("Доза N (мл)", value=0.0)
    added_no3 = (dose_n * conc_n) / tank_vol

with c2:
    conc_p = st.number_input("PO4 (г/л)", value=5.0)
    dose_p = st.number_input("Доза P (мл)", value=0.0)
    added_po4 = (dose_p * conc_p) / tank_vol

with c3:
    conc_k = st.number_input("K (г/л)", value=20.0)
    dose_k = st.number_input("Доза K (мл)", value=0.0)
    added_k = (dose_k * conc_k) / tank_vol

with c4:
    conc_fe = st.number_input("Fe (г/л)", value=1.0)
    dose_fe = st.number_input("Доза Fe (мл)", value=0.0)
    added_fe = (dose_fe * conc_fe) / tank_vol

# --- 4. ПІДСУМОК ---
total_no3 = after_w_no3 + added_no3
total_po4 = after_w_po4 + added_po4
total_k = after_w_k + added_k

# CO2 (з попередженням)
co2 = 3 * kh * (10**(7 - ph))

# Правильний Redfield (молярний)
redfield = ((total_no3 / 62) / (total_po4 / 95)) if total_po4 > 0 else 0

st.caption("⚠️ CO2 коректний тільки для KH-залежних систем без кислот (ADA, торф).")

st.divider()

# --- 5. ПРОГНОЗ ---
st.header("📈 Прогноз")

colp1, colp2 = st.columns(2)

with colp1:
    daily_no3 = st.number_input("Споживання NO3 / день", value=2.0)
    daily_po4 = st.number_input("Споживання PO4 / день", value=0.2)

with colp2:
    days = st.slider("Днів прогнозу", 1, 14, 7)

days_range = list(range(days + 1))

no3_trend = [max(total_no3 - daily_no3 * d, 0) for d in days_range]
po4_trend = [max(total_po4 - daily_po4 * d, 0) for d in days_range]

df = pd.DataFrame({
    "Day": days_range,
    "NO3": no3_trend,
    "PO4": po4_trend
}).set_index("Day")

st.line_chart(df)

st.divider()

# --- 6. ПІДБІР ДОЗИ ---
st.header("🎯 Підібрати дозу")

target_no3 = st.number_input("Цільовий NO3", value=20.0)

needed_no3 = target_no3 - after_w_no3
dose_needed = (needed_no3 * tank_vol) / conc_n if conc_n > 0 else 0

st.write(f"Потрібно внести: {max(dose_needed,0):.1f} мл")

st.divider()

# --- 7. ВІЗУАЛІЗАЦІЯ ---
st.header("📊 Результат")

r1, r2, r3, r4 = st.columns(4)

r1.metric("NO3", f"{total_no3:.1f}")
r2.metric("PO4", f"{total_po4:.2f}")
r3.metric("K", f"{total_k:.1f}")
r4.metric("CO2", f"{co2:.1f}")

st.subheader("Аналіз")

# CO2
if co2 > 40:
    st.error("CO2 занадто високий")
elif 15 <= co2 <= 35:
    st.success("CO2 в нормі")
else:
    st.warning("CO2 низький")

# Redfield
if 14 <= redfield <= 20:
    st.success(f"Redfield OK ({redfield:.1f})")
else:
    st.warning(f"Redfield поза нормою ({redfield:.1f})")

# K/GH
k_target = gh * 1.5
if total_k < k_target:
    st.error(f"K низький (ціль: {k_target:.1f})")
else:
    st.success("K достатній")

# Токсичність
if total_no3 > 50:
    st.error("NO3 небезпечно високий")

if total_po4 > 3:
    st.warning("PO4 високий — ризик водоростей")

if added_fe > 0.5:
    st.warning("Забагато Fe")

if added_fe > 0:
    st.info(f"Fe додано: {added_fe:.2f}")
