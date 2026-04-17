import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V9", layout="wide")
st.title("🌿 Toxicode Aquarium System V9 Ecosystem Engine")


# ---------------- HELPERS ----------------
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)


def get_ml_dose(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0.0


# ---------------- STABILITY + ECOSYSTEM ENGINE ----------------
def ecosystem_engine(no3, po4, k, gh, kh, ph, redfield_target):

    # --- nutrient stress ---
    def nutrient_score(x, low, high):
        if x < low:
            return x / low if low > 0 else 0
        if x > high:
            return high / x
        return 1.0

    n_score = nutrient_score(no3, 5, 25)
    p_score = nutrient_score(po4, 0.2, 1.5)
    k_score = nutrient_score(k, 10, 30)

    # --- Redfield ---
    ratio = no3 / po4 if po4 > 0 else 0
    redfield_score = 1 / (1 + abs((ratio - redfield_target) / redfield_target)) if redfield_target > 0 else 1

    # --- CO2 stability ---
    co2 = 3 * kh * (10 ** (7 - ph))
    co2_score = 1.0 if 15 <= co2 <= 35 else 0.6

    # --- final ecosystem stability ---
    stability = (
        0.35 * n_score +
        0.25 * p_score +
        0.15 * k_score +
        0.25 * redfield_score
    ) * co2_score

    return clamp(stability, 0.05, 1.0), ratio, co2


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм (л)", value=200.0)

    st.subheader("🎯 Цілі")
    target_no3 = st.number_input("NO3 target", value=15.0)
    target_po4 = st.number_input("PO4 target", value=1.0)
    target_k = st.number_input("K target", value=15.0)

    st.subheader("⚙️ Модель")
    redfield_target = st.slider("Redfield (N:1P)", 5, 30, 15)
    days = st.slider("Прогноз", 1, 14, 7)


# ---------------- 1. CONSUMPTION ----------------
st.header("📉 1. Споживання")

consumption = {}

with st.expander("Історичні дані"):
    tabs = st.tabs(["NO3", "PO4", "K"])

    def calc(tab, name, key):
        with tab:
            c1, c2, c3 = st.columns(3)

            start = c1.number_input(f"{name} старт", value=15.0, key=f"s_{key}")
            end = c2.number_input(f"{name} кінець", value=10.0, key=f"e_{key}")
            added = c3.number_input(f"Внесено {name}", value=0.0, key=f"a_{key}")

            c4, c5 = st.columns(2)
            water = c4.number_input("Підміна (л)", value=0.0, key=f"w_{key}")
            d = c5.number_input("Днів", value=7, min_value=1, key=f"d_{key}")

            pct = water / tank_vol if tank_vol > 0 else 0

            cons = (start * (1 - pct) + added - end) / d
            consumption[name] = max(cons, 0)

            st.info(f"{name}: {consumption[name]:.2f} мг/л/д")

    calc(tabs[0], "NO3", "no3")
    calc(tabs[1], "PO4", "po4")
    calc(tabs[2], "K", "k")


# ---------------- 2. STATE ----------------
st.header("📋 2. Поточний стан")

c1, c2, c3 = st.columns(3)

with c1:
    no3 = st.number_input("NO3", value=10.0)
    po4 = st.number_input("PO4", value=0.5)
    k = st.number_input("K", value=10.0)

with c2:
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=3)
    ph = st.number_input("pH", value=6.8)

with c3:
    d_no3 = st.number_input("NO3 споживання", value=consumption.get("NO3", 2.0))
    d_po4 = st.number_input("PO4 споживання", value=consumption.get("PO4", 0.1))
    d_k = st.number_input("K споживання", value=consumption.get("K", 1.0))


# ---------------- ENGINE ----------------
stability, ratio, co2 = ecosystem_engine(no3, po4, k, gh, kh, ph, redfield_target)


# ---------------- 3. DOSING ----------------
st.header("💧 Внесення")

change = st.number_input("Підміна (л)", value=50.0)
pct = change / tank_vol if tank_vol > 0 else 0

no3 = no3 * (1 - pct)
po4 = po4 * (1 - pct)
k = k * (1 - pct)

c1, c2, c3 = st.columns(3)

with c1:
    cn = st.number_input("N г/л", value=50.0)
    dn = st.number_input("N мл", value=0.0)

with c2:
    cp = st.number_input("P г/л", value=5.0)
    dp = st.number_input("P мл", value=0.0)

with c3:
    ck = st.number_input("K г/л", value=20.0)
    dk = st.number_input("K мл", value=0.0)

start_n = no3 + (dn * cn / tank_vol)
start_p = po4 + (dp * cp / tank_vol)
start_k = k + (dk * ck / tank_vol)


# ---------------- 4. ZERO CROSS SIMULATION ----------------
st.header("📈 3. Прогноз (Ecosystem Simulation)")

forecast = []

n, p, k_ = start_n, start_p, start_k

warn = {"NO3": None, "PO4": None, "K": None}

for d in range(days + 1):

    forecast.append({"Day": d, "NO3": n, "PO4": p, "K": k_})

    if warn["NO3"] is None and n < 3:
        warn["NO3"] = d
    if warn["PO4"] is None and p < 0.2:
        warn["PO4"] = d
    if warn["K"] is None and k_ < 8:
        warn["K"] = d

    # cycle
    n += (dn * cn / tank_vol)
    p += (dp * cp / tank_vol)
    k_ += (dk * ck / tank_vol)

    n -= d_no3
    p -= d_po4
    k_ -= d_k

    n = clamp(n, 0, 100)
    p = clamp(p, 0, 10)
    k_ = clamp(k_, 0, 100)

df = pd.DataFrame(forecast)
st.line_chart(df.set_index("Day"))

st.subheader("⚠️ Виснаження")
st.write(warn)


# ---------------- 5. ANALYSIS ----------------
st.header("📊 4. Аналіз")

st.metric("Ecosystem Stability", f"{stability:.2f}")
st.metric("Redfield Ratio", f"{ratio:.1f}:1")
st.metric("CO2", f"{co2:.1f} mg/L")

if stability < 0.4:
    st.error("Система нестабільна — високий ризик водоростей")

if ratio < redfield_target:
    st.warning("Дефіцит NO3 відносно PO4")

if ratio > redfield_target:
    st.warning("Дефіцит PO4 відносно NO3")


# ---------------- 6. DOSING PLAN ----------------
st.header("📦 Рекомендації")

f = df.iloc[-1]

ml_n = get_ml_dose(f["NO3"], target_no3, cn, tank_vol)
ml_p = get_ml_dose(f["PO4"], target_po4, cp, tank_vol)
ml_k = get_ml_dose(f["K"], target_k, ck, tank_vol)

st.write(f"""
N: {ml_n:.1f} мл
P: {ml_p:.1f} мл
K: {ml_k:.1f} мл
""")
