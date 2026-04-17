import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V7", layout="wide")
st.title("🌿 Toxicode Aquarium System V7 Pro")

# ---------------- 1. SIDEBAR: ГЛОБАЛЬНІ ПАРАМЕТРИ ----------------
with st.sidebar:
    st.header("📏 Конфігурація системи")
    tank_vol = st.number_input("Об'єм акваріума (л)", value=200.0, step=1.0)
    
    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0)
    target_tds = st.number_input("Ціль TDS", value=120.0)
    
    st.divider()
    st.subheader("📅 Прогноз")
    days = st.slider("Днів прогнозу", 1, 14, 7)

# ---------------- 2. ОСНОВНІ ПАРАМЕТРИ (ТЕСТИ) ----------------
st.header("📋 Поточні параметри води")
col_base1, col_base2, col_base3 = st.columns(3)

with col_base1:
    no3 = st.number_input("Тест NO3 (мг/л)", value=10.0)
    po4 = st.number_input("Тест PO4 (мг/л)", value=0.5)
    k = st.number_input("Тест K (мг/л)", value=10.0)

with col_base2:
    gh = st.number_input("GH (Загальна)", value=6)
    kh = st.number_input("KH (Карбонатна)", value=4)
    ph = st.number_input("pH (Кислотність)", value=6.8)

with col_base3:
    base_tds = st.number_input("Поточний TDS", value=150.0)
    daily_no3 = st.number_input("Споживання NO3/день", value=2.0)
    daily_po4 = st.number_input("Споживання PO4/день", value=0.1)

st.divider()

# ---------------- 3. ПІДМІНА ТА РЕМІНЕРАЛІЗАЦІЯ ----------------
st.header("💧 Підміна та Ремінералізація")
col_w1, col_w2, col_w3 = st.columns(3)

with col_w1:
    change_l = st.number_input("Літри підміни (л)", value=50.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.write(f"📊 Обсяг підміни: **{pct*100:.1f}%**")

with col_w2:
    water_no3 = st.number_input("NO3 у новій воді", value=0.0)
    water_po4 = st.number_input("PO4 у новій воді", value=0.0)

with col_w3:
    water_tds = st.number_input("TDS нової води (після ремінералізації)", value=110.0)

# Розрахунок після підміни
after_no3 = no3 * (1 - pct) + (water_no3 * pct)
after_po4 = po4 * (1 - pct) + (water_po4 * pct)
after_tds = base_tds * (1 - pct) + (water_tds * pct)

st.info(f"📉 **Прогноз після підміни:** NO3: {after_no3:.1f} | PO4: {after_po4:.2f} | **TDS: {after_tds:.0f}**")

st.divider()

# ---------------- 4. ДОЗУВАННЯ ДОБРИВ ----------------
st.header("🧪 Дозування добрив (г/л)")
c_d1, c_d2, c_d3, c_d4 = st.columns(4)

with c_d1:
    st.markdown("**Азот (N)**")
    conc_n = st.number_input("NO3 г/л", value=50.0, key="cn")
    dose_n = st.number_input("Доза N мл", value=0.0, key="dn")
    add_no3 = (dose_n * conc_n) / tank_vol

with c_d2:
    st.markdown("**Фосфор (P)**")
    conc_p = st.number_input("PO4 г/л", value=5.0, key="cp")
    dose_p = st.number_input("Доза P мл", value=0.0, key="dp")
    add_po4 = (dose_p * conc_p) / tank_vol

with c_d3:
    st.markdown("**Калій (K)**")
    conc_k = st.number_input("K г/л", value=20.0, key="ck")
    dose_k = st.number_input("Доза K мл", value=0.0, key="dk")
    add_k = (dose_k * conc_k) / tank_vol

with c_d4:
    st.markdown("**Залізо (Fe)**")
    conc_fe = st.number_input("Fe г/л", value=1.0, key="cfe")
    dose_fe = st.number_input("Доза Fe мл", value=0.0, key="dfe")
    add_fe = (dose_fe * conc_fe) / tank_vol

final_no3 = after_no3 + add_no3
final_po4 = after_po4 + add_po4
final_k = k + add_k

# ---------------- 5. ГРАФІК ПРОГНОЗУ ----------------
st.header("📈 Прогноз динаміки споживання")
forecast = []
for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(final_no3 - daily_no3 * d, 0),
        "PO4": max(final_po4 - daily_po4 * d, 0)
    })
df = pd.DataFrame(forecast).set_index("День")
st.line_chart(df)

st.divider()

# ---------------- 6. АНАЛІЗ ТА ПЛАН ДІЙ ----------------
st.header("📊 Аналіз та Рекомендації Toxicode")
res1, res2, res3, res4 = st.columns(4)

co2 = 3 * kh * (10**(7 - ph))
ratio = final_no3 / final_po4 if final_po4 > 0 else 0
k_target = gh * 1.5

with res1:
    st.metric("CO2 (мг/л)", f"{co2:.1f}")
    if 15 <= co2 <= 35: st.success("CO2 OK")
    else: st.warning("Перевірте CO2")

with res2:
    st.metric("Редфілд", f"{ratio:.1f}")
    if 10 <= ratio <= 22: st.success("Баланс OK")
    else: st.error("Дисбаланс N/P")

with res3:
    st.metric("K/GH Баланс", f"{final_k:.1f}")
    if final_k >= k_target: st.success("Транспорт OK")
    else: st.error(f"Мало K (ціль {k_target})")

with res4:
    st.metric("Прогноз TDS", f"{after_tds:.0f}")
    if abs(after_tds - target_tds) < 10: st.success("TDS в нормі")
    else: st.info("TDS відхилено")

st.divider()

# РОЗУМНИЙ ПЛАН
future_no3 = df.iloc[-1]["NO3"]
future_po4 = df.iloc[-1]["PO4"]

col_plan1, col_plan2 = st.columns(2)

with col_plan1:
    st.subheader("📍 Стан на кінець прогнозу")
    if future_no3 < target_no3:
        need_n = (target_no3 - future_no3) * tank_vol / conc_n
        st.warning(f"Додати **{need_n:.1f} мл** NO3 для цілі {target_no3} мг/л")
    else:
        st.success("Нітратів достатньо")

with col_plan2:
    if future_po4 < target_po4:
        need_p = (target_po4 - future_po4) * tank_vol / conc_p
        st.warning(f"Додати **{need_p:.1f} мл** PO4 для цілі {target_po4} мг/л")
    else:
        st.success("Фосфатів достатньо")
