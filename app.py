import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Toxicode V6", layout="wide")
st.title("🌿 Toxicode Aquarium System V6")

# ---------------- ОБʼЄМ ----------------
st.header("📏 Обʼєм")
tank_vol = st.number_input("Чистий обʼєм (л)", value=200.0)

# ---------------- ТЕСТИ ----------------
st.header("📋 Поточні параметри")
col1, col2 = st.columns(2)

with col1:
    no3 = st.number_input("NO3 (мг/л)", value=10.0)
    po4 = st.number_input("PO4 (мг/л)", value=0.5)
    k = st.number_input("K (мг/л)", value=10.0)

with col2:
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=4)
    ph = st.number_input("pH", value=6.8)

# ---------------- ПІДМІНА ----------------
st.header("💧 Підміна")

change_l = st.number_input("Літри підміни", value=50.0)

new_no3 = st.number_input("NO3 у новій воді", value=0.0)
new_po4 = st.number_input("PO4 у новій воді", value=0.0)

pct = change_l / tank_vol if tank_vol > 0 else 0

after_no3 = no3*(1-pct) + new_no3*pct
after_po4 = po4*(1-pct) + new_po4*pct

st.write(f"Підміна: {pct*100:.1f}%")
st.write(f"Після підміни NO3: {after_no3:.2f}, PO4: {after_po4:.2f}")

# ---------------- ДОБРИВА ----------------
st.header("🧪 Дозування")

c1, c2, c3 = st.columns(3)

with c1:
    conc_n = st.number_input("NO3 г/л", value=50.0)
    dose_n = st.number_input("Доза NO3 мл", value=0.0)
    add_no3 = (dose_n * conc_n) / tank_vol

with c2:
    conc_p = st.number_input("PO4 г/л", value=5.0)
    dose_p = st.number_input("Доза PO4 мл", value=0.0)
    add_po4 = (dose_p * conc_p) / tank_vol

with c3:
    conc_k = st.number_input("K г/л", value=20.0)
    dose_k = st.number_input("Доза K мл", value=0.0)
    add_k = (dose_k * conc_k) / tank_vol

final_no3 = after_no3 + add_no3
final_po4 = after_po4 + add_po4
final_k = k + add_k

# ---------------- СПОЖИВАННЯ ----------------
st.header("📉 Споживання (емпіричне)")

daily_no3 = st.number_input("Споживання NO3 мг/л/день", value=2.0)
daily_po4 = st.number_input("Споживання PO4 мг/л/день", value=0.1)

# ---------------- ПРОГНОЗ ----------------
st.header("📈 Прогноз")

days = st.slider("Днів", 1, 14, 7)

forecast = []

for d in range(days):
    forecast.append({
        "day": d,
        "no3": max(final_no3 - daily_no3*d, 0),
        "po4": max(final_po4 - daily_po4*d, 0)
    })

df = pd.DataFrame(forecast)

st.line_chart(df.set_index("day"))

# ---------------- АНАЛІЗ ----------------
st.header("📊 Аналіз")

co2 = 3 * kh * (10**(7 - ph))
ratio = final_no3 / final_po4 if final_po4 > 0 else 0

st.metric("CO2", f"{co2:.1f}")
st.metric("NO3/PO4", f"{ratio:.1f}")

# ---------------- РЕКОМЕНДАЦІЯ ----------------
target_no3 = st.number_input("Ціль NO3", value=15.0)

future_no3 = df.iloc[-1]["no3"]

if future_no3 < target_no3:
    need = target_no3 - future_no3
    st.warning(f"Додати NO3: {need:.1f} мг/л")
else:
    st.success("Баланс нормальний")
