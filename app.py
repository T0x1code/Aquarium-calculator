import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V7.3", layout="wide")
st.title("🌿 Toxicode Aquarium System V7.3 Pro")

# ---------------- 1. SIDEBAR: ГЛОБАЛЬНІ ЦІЛІ ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0)
    
    st.divider()
    st.subheader("🎯 Цільові показники (Target)")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0)
    target_tds = st.number_input("Ціль TDS", value=120.0)
    
    st.divider()
    days = st.slider("Днів прогнозу", 1, 14, 7)

# ---------------- 2. РОЗРАХУНОК РЕАЛЬНОГО СПОЖИВАННЯ ----------------
st.header("📉 1. Калькулятор споживання (замість блокнота)")
with st.expander("Розгорнути для розрахунку щоденного споживання за минулий тиждень"):
    col_log1, col_log2, col_log3 = st.columns(3)
    with col_log1:
        prev_test = st.number_input("Попередній тест NO3 (мг/л)", value=15.0)
        curr_test = st.number_input("Сьогоднішній тест NO3 (мг/л)", value=10.0)
    with col_log2:
        total_added = st.number_input("Скільки всього внесли за цей час (мг/л)", value=0.0)
        days_passed = st.number_input("Скільки днів пройшло", value=7)
    with col_log3:
        real_cons = (prev_test + total_added - curr_test) / days_passed if days_passed > 0 else 0
        st.metric("Твоє реальне споживання", f"{real_cons:.2f} мг/л/день")
        st.caption("Використовуй це число у блоці нижче.")

st.divider()

# ---------------- 3. ПОТОЧНІ ПАРАМЕТРИ ----------------
st.header("📋 2. Поточні параметри та налаштування")
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Лабораторія (Тести)")
    no3 = st.number_input("Поточний NO3 мг/л", value=10.0)
    po4 = st.number_input("Поточний PO4 мг/л", value=0.5)
    k = st.number_input("Поточний K мг/л", value=10.0)
    base_tds = st.number_input("Поточний TDS", value=150.0)

with c2:
    st.subheader("Жорсткість / pH")
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=4)
    ph = st.number_input("pH", value=6.8)

with c3:
    st.subheader("Споживання (мг/л/день)")
    daily_no3 = st.number_input("Споживання NO3", value=2.0, step=0.1)
    daily_po4 = st.number_input("Споживання PO4", value=0.1, step=0.01)
    daily_k = st.number_input("Споживання K", value=1.0, step=0.1)

st.divider()

# ---------------- 4. ПІДМІНА ТА ДОБРИВА ----------------
col_act1, col_act2 = st.columns([1, 2])

with col_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри підміни (л)", value=50.0)
    water_tds = st.number_input("TDS нової води", value=110.0)
    
    pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3 = no3 * (1 - pct) 
    after_po4 = po4 * (1 - pct)
    after_k = k * (1 - pct)
    after_tds = base_tds * (1 - pct) + (water_tds * pct)

with col_act2:
    st.header("🧪 Дозування добрив (г/л)")
    cd1, cd2, cd3 = st.columns(3)
    conc_n = cd1.number_input("N розчин г/л", value=50.0, key="cn")
    dose_n = cd1.number_input("Доза N мл", value=0.0, key="dn")
    
    conc_p = cd2.number_input("P розчин г/л", value=5.0, key="cp")
    dose_p = cd2.number_input("Доза P мл", value=0.0, key="dp")
    
    conc_k = cd3.number_input("K розчин г/л", value=20.0, key="ck")
    dose_k = cd3.number_input("Доза K мл", value=0.0, key="dk")

# Розрахунок старту
start_no3 = after_no3 + (dose_n * conc_n / tank_vol)
start_po4 = after_po4 + (dose_p * conc_p / tank_vol)
start_k = after_k + (dose_k * conc_k / tank_vol)

# ---------------- 5. ПРОГНОЗ ТА ГРАФІК ----------------
st.header("📈 3. Прогноз динаміки")
forecast_data = []
for d in range(days + 1):
    forecast_data.append({
        "День": d,
        "NO3": max(start_no3 - daily_no3 * d, 0),
        "PO4": max(start_po4 - daily_po4 * d, 0),
        "K": max(start_k - daily_k * d, 0)
    })
df_forecast = pd.DataFrame(forecast_data).set_index("День")
st.line_chart(df_forecast)

# ---------------- 6. АНАЛІЗ ТА ПЛАН ----------------
st.header("📊 4. Аналіз та Коригування")
res1, res2, res3, res4 = st.columns(4)

co2 = 3 * kh * (10**(7 - ph))
ratio = start_no3 / start_po4 if start_po4 > 0 else 0
k_target_min = gh * 1.5

res1.metric("CO2", f"{co2:.1f} мг/л")
res2.metric("Редфілд", f"{ratio:.1f}")
res3.metric("K/GH", f"{start_k:.1f}", f"Мін: {k_target_min:.1f}")
res4.metric("TDS прогноз", f"{after_tds:.0f}")

st.divider()

# ПЛАН ДІЙ
st.subheader(f"📍 Коригувальна доза (щоб вийти на цілі через {days} дн.)")
st.caption("Це НЕ щоденна доза, а кількість мл, яку треба внести додатково до графіка, щоб перекрити дефіцит прогнозу.")

f_no3 = df_forecast.iloc[-1]["NO3"]
f_po4 = df_forecast.iloc[-1]["PO4"]
f_k = df_forecast.iloc[-1]["K"]

plan1, plan2, plan3 = st.columns(3)

def get_ml(current, target, conc, vol):
    if current < target:
        ml = ((target - current) * vol) / conc
        return ml
    return 0

with plan1:
    ml_n = get_ml(f_no3, target_no3, conc_n, tank_vol)
    if ml_n > 0: st.info(f"**Азот (N):** Додати **{ml_n:.1f} мл**")
    else: st.success("N в межах цілі")

with plan2:
    ml_p = get_ml(f_po4, target_po4, conc_p, tank_vol)
    if ml_p > 0: st.info(f"**Фосфор (P):** Додати **{ml_p:.1f} мл**")
    else: st.success("P в межах цілі")

with plan3:
    ml_k = get_ml(f_k, target_k, conc_k, tank_vol)
    if ml_k > 0: st.info(f"**Калій (K):** Додати **{ml_k:.1f} мл**")
    else: st.success("K в межах цілі")

st.markdown("---")
st.warning("⚠️ **Дисклеймер:** Всі розрахунки математичні. Коригуйте дози поступово.")
