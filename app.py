import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V6", layout="wide")
st.title("🌿 Toxicode Aquarium System V6 Pro")

# ---------------- 1. ЗАГАЛЬНІ ПАРАМЕТРИ ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий обʼєм акваріума (л)", value=200.0, step=1.0)
    days = st.slider("Прогноз на (днів)", 1, 14, 7)
    target_no3 = st.number_input("Цільовий NO3 (мг/л)", value=15.0)

# ---------------- 2. ТЕСТИ ТА ПІДМІНА ----------------
col_base1, col_base2 = st.columns(2)

with col_base1:
    st.header("📋 Поточні тести")
    c_t1, c_t2, c_t3 = st.columns(3)
    no3 = c_t1.number_input("NO3 (мг/л)", value=10.0)
    po4 = c_t2.number_input("PO4 (мг/л)", value=0.5)
    k = c_t3.number_input("K (мг/л)", value=10.0)
    
    c_t4, c_t5, c_t6 = st.columns(3)
    gh = c_t4.number_input("GH", value=6)
    kh = c_t5.number_input("KH", value=4)
    ph = c_t6.number_input("pH", value=6.8)

with col_base2:
    st.header("💧 Підміна води")
    change_l = st.number_input("Літри підміни (л)", value=50.0)
    c_w1, c_w2 = st.columns(2)
    new_no3 = c_w1.number_input("NO3 у новій воді", value=0.0)
    new_po4 = c_w2.number_input("PO4 у новій воді", value=0.0)

# Розрахунок після підміни
pct = change_l / tank_vol if tank_vol > 0 else 0
after_no3 = no3 * (1 - pct) + (new_no3 * pct)
after_po4 = po4 * (1 - pct) + (new_po4 * pct)

st.divider()

# ---------------- 3. ДОЗУВАННЯ ----------------
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

st.divider()

# ---------------- 4. СПОЖИВАННЯ ТА ПРОГНОЗ ----------------
col_f1, col_f2 = st.columns([1, 2])

with col_f1:
    st.header("📉 Споживання")
    daily_no3 = st.number_input("NO3 мг/л/день", value=2.0)
    daily_po4 = st.number_input("PO4 мг/л/день", value=0.1)

    # Аналіз CO2 та Редфілда
    co2 = 3 * kh * (10**(7 - ph))
    ratio = final_no3 / final_po4 if final_po4 > 0 else 0
    k_target = gh * 1.5

with col_f2:
    st.header("📈 Прогноз динаміки")
    forecast = []
    for d in range(days + 1):
        forecast.append({
            "День": d,
            "NO3 (Нітрат)": max(final_no3 - daily_no3 * d, 0),
            "PO4 (Фосфат)": max(final_po4 - daily_po4 * d, 0)
        })
    df = pd.DataFrame(forecast).set_index("День")
    st.line_chart(df)

st.divider()

# ---------------- 5. ЕКСПЕРТНИЙ АНАЛІЗ TOXICODE ----------------
st.header("📊 Аналіз та Рекомендації")
res1, res2, res3 = st.columns(3)

# Панель CO2
with res1:
    st.metric("CO2 (мг/л)", f"{co2:.1f}")
    if co2 > 40: st.error("Критичний рівень CO2!")
    elif 15 <= co2 <= 35: st.success("CO2 в нормі")
    else: st.warning("Недостатньо CO2")

# Панель NO3/PO4
with res2:
    st.metric("Співвідношення Редфілда", f"{ratio:.1f}")
    if 10 <= ratio <= 22: st.success("Ідеальний баланс")
    elif ratio < 10: st.error("Ризик синьо-зелених (мало N)")
    else: st.warning("Ризик ксенококусу (мало P)")

# Панель Калію
with res3:
    st.metric("Калій (K)", f"{final_k:.1f}", f"Ціль: {k_target:.1f}")
    if final_k < k_target: st.error("Блокування азоту! Додайте K.")
    else: st.success("Транспорт іонів OK")

st.divider()

# ---------------- 6. РОЗУМНИЙ ПЛАН ДІЙ ----------------
st.header("📝 План дій")
future_no3 = df.iloc[-1]["NO3 (Нітрат)"]

if future_no3 < target_no3:
    need_mg_l = target_no3 - future_no3
    need_ml = (need_mg_l * tank_vol) / conc_n if conc_n > 0 else 0
    st.warning(f"⚠️ Через {days} днів нітрат впаде до {future_no3:.1f} мг/л.")
    st.info(f"💡 Рекомендація: Додайте **{need_ml:.1f} мл** вашого добрива NO3, щоб вийти на ціль {target_no3} мг/л.")
else:
    st.success(f"✅ Баланс стабільний. Через {days} днів нітрат буде на рівні {future_no3:.1f} мг/л.")

if add_fe > 0:
    st.caption(f"Доза заліза (Fe): {add_fe:.2f} мг/л внесена в систему.")
