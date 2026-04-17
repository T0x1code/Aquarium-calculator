import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V7.2", layout="wide")
st.title("🌿 Toxicode Aquarium System V7.2 Pro")

# ---------------- 1. SIDEBAR: ГЛОБАЛЬНІ ПАРАМЕТРИ ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)
    
    st.divider()
    st.subheader("🎯 Цільові показники (Target)")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0)
    target_tds = st.number_input("Ціль TDS", value=120.0)
    
    st.divider()
    days = st.slider("Днів прогнозу", 1, 14, 7)

# ---------------- 2. ПОТОЧНІ ТЕСТИ ТА СПОЖИВАННЯ ----------------
st.header("📋 Поточні параметри та Споживання")
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Лабораторія")
    no3 = st.number_input("Тест NO3 мг/л", value=10.0)
    po4 = st.number_input("Тест PO4 мг/л", value=0.5)
    k = st.number_input("Тест K мг/л", value=10.0)
    base_tds = st.number_input("Поточний TDS", value=150.0)

with c2:
    st.subheader("Жорсткість/pH")
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=4)
    ph = st.number_input("pH", value=6.8)

with c3:
    st.subheader("Споживання (мг/л/день)")
    daily_no3 = st.number_input("Апетит по NO3", value=2.0, step=0.1)
    daily_po4 = st.number_input("Апетит по PO4", value=0.1, step=0.01)
    daily_k = st.number_input("Апетит по K", value=1.0, step=0.1)

st.divider()

# ---------------- 3. ПІДМІНА ТА ДОБРИВА ----------------
col_act1, col_act2 = st.columns([1, 2])

with col_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри підміни (л)", value=50.0)
    water_tds = st.number_input("TDS нової води", value=110.0)
    
    pct = change_l / tank_vol if tank_vol > 0 else 0
    # Параметри після змішування (очищення води)
    after_no3 = no3 * (1 - pct) 
    after_po4 = po4 * (1 - pct)
    after_k = k * (1 - pct)
    after_tds = base_tds * (1 - pct) + (water_tds * pct)

with col_act2:
    st.header("🧪 Дозування добрив (г/л)")
    cd1, cd2, cd3 = st.columns(3)
    
    with cd1:
        conc_n = st.number_input("N розчин г/л", value=50.0, key="cn")
        dose_n = st.number_input("Доза N мл", value=0.0, key="dn")
    with cd2:
        conc_p = st.number_input("P розчин г/л", value=5.0, key="cp")
        dose_p = st.number_input("Доза P мл", value=0.0, key="dp")
    with cd3:
        conc_k = st.number_input("K розчин г/л", value=20.0, key="ck")
        dose_k = st.number_input("Доза K мл", value=0.0, key="dk")

# Розрахунок стартових значень ПІСЛЯ підміни ТА внесення добрив
start_no3 = after_no3 + (dose_n * conc_n / tank_vol)
start_po4 = after_po4 + (dose_p * conc_p / tank_vol)
start_k = after_k + (dose_k * conc_k / tank_vol)

# ---------------- 4. ПРОГНОЗ (ГРАФІК) ----------------
st.header("📈 Прогноз динаміки (без урахування нових доз)")
forecast_data = []
for d in range(days + 1):
    forecast_data.append({
        "День": d,
        "NO3 (Нітрат)": max(start_no3 - daily_no3 * d, 0),
        "PO4 (Фосфат)": max(start_po4 - daily_po4 * d, 0),
        "K (Калій)": max(start_k - daily_k * d, 0)
    })
df_forecast = pd.DataFrame(forecast_data).set_index("День")
st.line_chart(df_forecast)

# ---------------- 5. АНАЛІЗ ТА РЕКОМЕНДАЦІЇ ----------------
st.header("📊 Аналіз та Розрахунок дефіциту")
res1, res2, res3, res4 = st.columns(4)

co2 = 3 * kh * (10**(7 - ph))
ratio = start_no3 / start_po4 if start_po4 > 0 else 0
k_target_min = gh * 1.5

res1.metric("CO2", f"{co2:.1f} мг/л")
res2.metric("Редфілд", f"{ratio:.1f}")
res3.metric("K:GH", f"{start_k:.1f}", f"Мін: {k_target_min:.1f}")
res4.metric("Прогноз TDS", f"{after_tds:.0f}")

st.divider()

# ФУНКЦІЯ РОЗРАХУНКУ
def get_advice(current_f, target, conc, vol):
    if current_f < target:
        diff = target - current_f
        ml = (diff * vol) / conc if conc > 0 else 0
        return diff, ml
    return 0, 0

# ПЛАН ДІЙ
st.subheader(f"📍 Стан через {days} дн. відносно ваших цілей")
f_no3 = df_forecast.iloc[-1]["NO3 (Нітрат)"]
f_po4 = df_forecast.iloc[-1]["PO4 (Фосфат)"]
f_k = df_forecast.iloc[-1]["K (Калій)"]

plan1, plan2, plan3 = st.columns(3)

with plan1:
    diff_n, ml_n = get_advice(f_no3, target_no3, conc_n, tank_vol)
    if diff_n > 0:
        st.info(f"**Азот (N):** Буде дефіцит {diff_n:.1f} мг/л. Математично це **{ml_n:.1f} мл** розчину.")
    else:
        st.success("Нітрат у межах цілі")

with plan2:
    diff_p, ml_p = get_advice(f_po4, target_po4, conc_p, tank_vol)
    if diff_p > 0:
        st.info(f"**Фосфор (P):** Буде дефіцит {diff_p:.2f} мг/л. Математично це **{ml_p:.1f} мл** розчину.")
    else:
        st.success("Фосфор у межах цілі")

with plan3:
    diff_k, ml_k = get_advice(f_k, target_k, conc_k, tank_vol)
    if diff_k > 0:
        st.info(f"**Калій (K):** Буде дефіцит {diff_k:.1f} мг/л. Математично це **{ml_k:.1f} мл** розчину.")
    else:
        st.success("Калій у межах цілі")

st.markdown("---")
st.warning("⚠️ **Дисклеймер:** Розрахунки є математичною моделлю. Завжди орієнтуйтеся на стан рослин та поведінку риб.")
