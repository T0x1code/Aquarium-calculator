import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.4", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.4 Dynamic")

# ---------------- HELPER ----------------
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def get_ml_dose(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0.0

# ---------------- 1. SIDEBAR ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)
    st.divider()
    st.subheader("🎯 Цільові значення")
    target_no3 = st.number_input("Ціль NO3", value=15.0)
    target_po4 = st.number_input("Ціль PO4", value=1.0)
    target_k = st.number_input("Ціль K", value=15.0)
    st.divider()
    st.subheader("⚙️ Модель")
    custom_redfield = st.slider("Редфілд (N:1P)", 5, 30, 15)
    days = st.slider("Прогноз (днів)", 1, 21, 7)
    data_quality = st.slider("Якість даних", 0.5, 1.0, 0.85)

# ---------------- 2. СПОЖИВАННЯ ----------------
st.header("📉 1. Аналіз споживання")
consumption_results = {}
with st.expander("Розрахувати споживання за тестами"):
    t_tabs = st.tabs(["NO3", "PO4", "K"])
    def calc_cons(tab, name, key):
        with tab:
            c1, c2, c3 = st.columns(3)
            start = c1.number_input(f"{name} старт", value=15.0, key=f"s_{key}")
            end = c2.number_input(f"{name} зараз", value=10.0, key=f"e_{key}")
            added = c3.number_input(f"Внесено за період", value=0.0, key=f"a_{key}")
            c4, c5 = st.columns(2)
            w_change = c4.number_input("Підміна (л)", value=0.0, key=f"w_{key}")
            d_local = c5.number_input("Днів періоду", value=7, min_value=1, key=f"d_{key}")
            pct = w_change / tank_vol if tank_vol > 0 else 0
            cons = ((start * (1 - pct) + added - end) / d_local) * data_quality
            val = max(cons, 0)
            consumption_results[name] = val
            st.info(f"**Споживання:** {val:.2f} мг/л/д")

    calc_cons(t_tabs[0], "NO3", "no3")
    calc_cons(t_tabs[1], "PO4", "po4")
    calc_cons(t_tabs[2], "K", "k")

# ---------------- 3. ПОТОЧНИЙ СТАН ----------------
st.header("📋 2. Поточний стан та Дозування")
col1, col2, col3 = st.columns(3)
with col1:
    no3_now = st.number_input("Тест NO3", value=10.0)
    po4_now = st.number_input("Тест PO4", value=0.5)
    k_now = st.number_input("Тест K", value=10.0)
with col2:
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=3)
    ph = st.number_input("pH", value=6.8)
with col3:
    daily_no3 = st.number_input("Споживання NO3 (д)", value=consumption_results.get("NO3", 2.0))
    daily_po4 = st.number_input("Споживання PO4 (д)", value=consumption_results.get("PO4", 0.1))
    daily_k = st.number_input("Споживання K (д)", value=consumption_results.get("K", 1.0))

# ---------------- 4. ПЛАН ВНЕСЕННЯ ----------------
st.subheader("🧪 Щоденне внесення добрив (мл/день)")
d_col1, d_col2, d_col3 = st.columns(3)
c_n = d_col1.number_input("Конц. N (г/л)", value=50.0)
daily_ml_n = d_col1.number_input("Доза N (мл/день)", value=0.0)
c_p = d_col2.number_input("Конц. P (г/л)", value=5.0)
daily_ml_p = d_col2.number_input("Доза P (мл/день)", value=0.0)
c_k = d_col3.number_input("Конц. K (г/л)", value=20.0)
daily_ml_k = d_col3.number_input("Доза K (мл/день)", value=0.0)

# ---------------- 5. ПРОГНОЗ ----------------
st.header("📈 3. Динамічний прогноз")
st.caption("Графік враховує щоденне споживання ТА щоденне внесення добрив.")

# Розрахунок стабільності (V8.2 logic)
ratio_now = no3_now / po4_now if po4_now > 0 else 0
stability = 1 / (1 + abs((ratio_now - custom_redfield) / custom_redfield))
adj_no3_cons = daily_no3 * stability
adj_po4_cons = daily_po4 * stability
adj_k_cons = daily_k * stability

forecast = []
curr_n, curr_p, curr_k = no3_now, po4_now, k_now

for d in range(days + 1):
    forecast.append({"День": d, "NO3": curr_n, "PO4": curr_p, "K": curr_k})
    # Щодня: + внесення - споживання
    curr_n = clamp(curr_n + (daily_ml_n * c_n / tank_vol) - adj_no3_cons, 0, 100)
    curr_p = clamp(curr_p + (daily_ml_p * c_p / tank_vol) - adj_po4_cons, 0, 15)
    curr_k = clamp(curr_k + (daily_ml_k * c_k / tank_vol) - adj_k_cons, 0, 100)

st.line_chart(pd.DataFrame(forecast).set_index("День"))

# ---------------- 6. АНАЛІЗ ----------------
st.header("📊 4. Аналіз та Рекомендації")
co2_val = 3 * kh * (10 ** (7 - ph))
k_min = gh * 1.5

col_adv, col_rep = st.columns([1.3, 1])
with col_adv:
    # Перевірка кінцевої точки прогнозу
    f_end = forecast[-1]
    if f_end["NO3"] < 2: st.error("🚨 **Критичний дефіцит N!** Доза не покриває споживання.")
    if f_end["PO4"] < 0.05: st.error("🚨 **Критичний дефіцит P!** Доза не покриває споживання.")
    
    st.info(f"""**Аналіз на кінець періоду ({days} дн.):**
* Стан NO3: {f_end['NO3']:.1f} мг/л (Ціль: {target_no3})
* Стан PO4: {f_end['PO4']:.1f} мг/л (Ціль: {target_po4})
* CO2: {co2_val:.1f} мг/л""")

with col_rep:
    st.subheader("📋 Звіт")
    report = f"""--- AQUA REPORT V8.4 ---
[ТЕСТИ] NO3:{no3_now} | PO4:{po4_now} | K:{k_now}
[ДОЗА/Д] N:{daily_ml_n}мл | P:{daily_ml_p}мл | K:{daily_ml_k}мл
[ПРОГНОЗ {days}д] NO3:{f_end['NO3']:.1f} | PO4:{f_end['PO4']:.1f}
-----------------------"""
    st.code(report, language="text")
