import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.3", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.3 Ultimate")

# ---------------- HELPERS ----------------
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def get_ml_dose(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0.0


# ---------------- STABILITY ENGINE ----------------
def stability_engine(no3, po4, k, custom_redfield):
    no3_min, no3_max = 5, 25
    po4_min, po4_max = 0.2, 1.5
    k_min, k_max = 10, 30

    def score(x, low, high):
        if x < low:
            return x / low if low != 0 else 0
        if x > high:
            return high / x
        return 1.0

    s_no3 = score(no3, no3_min, no3_max)
    s_po4 = score(po4, po4_min, po4_max)
    s_k = score(k, k_min, k_max)

    ratio = no3 / po4 if po4 > 0 else 0
    redfield_score = 1 / (1 + abs((ratio - custom_redfield) / custom_redfield)) if custom_redfield > 0 else 1

    stability = (0.5 * s_no3 + 0.3 * s_po4 + 0.2 * s_k) * redfield_score

    return clamp(stability, 0.05, 1.0), ratio


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)

    st.divider()
    st.subheader("🎯 Цілі")
    target_no3 = st.number_input("Ціль NO3", value=15.0)
    target_po4 = st.number_input("Ціль PO4", value=1.0)
    target_k = st.number_input("Ціль K", value=15.0)

    st.divider()
    st.subheader("⚙️ Модель")
    custom_redfield = st.slider("Редфілд (N:1P)", 5, 30, 15)
    days = st.slider("Прогноз (днів)", 1, 14, 7)


# ---------------- 1. СПОЖИВАННЯ ----------------
st.header("📉 1. Споживання")

consumption_results = {}

with st.expander("Минулі дані"):
    tabs = st.tabs(["NO3", "PO4", "K"])

    def calc(tab, name, key):
        with tab:
            c1, c2, c3 = st.columns(3)

            start = c1.number_input(f"{name} старт", value=15.0, key=f"s_{key}")
            end = c2.number_input(f"{name} кінець", value=10.0, key=f"e_{key}")
            added = c3.number_input(f"Внесено {name}", value=0.0, key=f"a_{key}")

            c4, c5 = st.columns(2)
            water_change = c4.number_input("Підміна (л)", value=0.0, key=f"w_{key}")
            days_local = c5.number_input("Днів", value=7, min_value=1, key=f"d_{key}")

            pct = water_change / tank_vol if tank_vol > 0 else 0

            cons = (start * (1 - pct) + added - end) / days_local
            val = max(cons, 0)

            consumption_results[name] = val
            st.info(f"{name}: {val:.2f} мг/л/д")

    calc(tabs[0], "NO3", "no3")
    calc(tabs[1], "PO4", "po4")
    calc(tabs[2], "K", "k")


# ---------------- 2. СТАН ----------------
st.header("📋 2. Поточний стан")

col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("NO3", value=10.0)
    po4_now = st.number_input("PO4", value=0.5)
    k_now = st.number_input("K", value=10.0)

with col2:
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=3)
    ph = st.number_input("pH", value=6.8)

with col3:
    daily_no3 = st.number_input("Споживання NO3", value=consumption_results.get("NO3", 2.0))
    daily_po4 = st.number_input("Споживання PO4", value=consumption_results.get("PO4", 0.1))
    daily_k = st.number_input("Споживання K", value=consumption_results.get("K", 1.0))


# ---------------- STABILITY ----------------
stability, ratio_now = stability_engine(no3_now, po4_now, k_now, custom_redfield)


# ---------------- 3. ВНЕСЕННЯ ----------------
st.header("💧 Внесення")

change_l = st.number_input("Підміна (л)", value=50.0)
pct = change_l / tank_vol if tank_vol > 0 else 0

after_no3 = no3_now * (1 - pct)
after_po4 = po4_now * (1 - pct)
after_k = k_now * (1 - pct)

c1, c2, c3 = st.columns(3)

with c1:
    c_n = st.number_input("N г/л", value=50.0)
    d_n = st.number_input("N мл", value=0.0)

with c2:
    c_p = st.number_input("P г/л", value=5.0)
    d_p = st.number_input("P мл", value=0.0)

with c3:
    c_k = st.number_input("K г/л", value=20.0)
    d_k = st.number_input("K мл", value=0.0)


start_no3 = after_no3 + (d_n * c_n / tank_vol)
start_po4 = after_po4 + (d_p * c_p / tank_vol)
start_k = after_k + (d_k * c_k / tank_vol)


# ---------------- 4. ПРОГНОЗ ----------------
st.header("📈 3. Прогноз")

forecast = []

curr_n, curr_p, curr_k = start_no3, start_po4, start_k

for d in range(days + 1):

    forecast.append({
        "День": d,
        "NO3": curr_n,
        "PO4": curr_p,
        "K": curr_k
    })

    # внесення
    curr_n += (d_n * c_n / tank_vol)
    curr_p += (d_p * c_p / tank_vol)
    curr_k += (d_k * c_k / tank_vol)

    # споживання
    curr_n -= daily_no3
    curr_p -= daily_po4
    curr_k -= daily_k


df = pd.DataFrame(forecast)
st.line_chart(df.set_index("День"))


# ---------------- 5. АНАЛІЗ ----------------
st.header("📊 4. Аналіз")

co2 = 3 * kh * (10 ** (7 - ph))
ratio_final = start_no3 / start_po4 if start_po4 > 0 else 0

k_min = gh * 1.5

st.metric("Stability Index", f"{stability:.2f}")
st.metric("Redfield Ratio", f"{ratio_now:.1f}:1")


if ratio_final < custom_redfield:
    st.warning("Низький NO3 відносно PO4")
elif ratio_final > custom_redfield:
    st.warning("Низький PO4 відносно NO3")

if k_now < k_min:
    st.error("Дефіцит K")

st.info(f"CO2: {co2:.1f} мг/л")


# ---------------- 6. ДОЗУВАННЯ ----------------
st.header("📦 Рекомендації")

f_end = df.iloc[-1]

ml_n = get_ml_dose(f_end["NO3"], target_no3, c_n, tank_vol)
ml_p = get_ml_dose(f_end["PO4"], target_po4, c_p, tank_vol)
ml_k = get_ml_dose(f_end["K"], target_k, c_k, tank_vol)

st.write(f"""
N: {ml_n:.1f} мл
P: {ml_p:.1f} мл
K: {ml_k:.1f} мл
""")
