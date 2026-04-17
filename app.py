import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.5", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.5 Ultimate")

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
    st.subheader("⚙️ Аналітика та Модель")
    custom_redfield = st.slider("Редфілд (N:1P)", 5, 30, 15)
    days = st.slider("Прогноз (днів)", 1, 21, 7)
    data_quality = st.slider("Якість даних (Data Quality)", 0.5, 1.0, 0.85)

# ---------------- 2. СПОЖИВАННЯ (РЕАЛЬНЕ) ----------------
st.header("📉 1. Калькулятор споживання")
consumption_results = {}

with st.expander("Аналіз минулого періоду (на основі тестів)"):
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

# ---------------- 3. ПОТОЧНИЙ СТАН ТА ДОЗУВАННЯ ----------------
st.header("📋 2. Поточний стан та Дозування")
col1, col2, col3 = st.columns(3)
with col1:
    no3_now = st.number_input("Тест NO3", value=10.0)
    po4_now = st.number_input("Тест PO4", value=0.5)
    k_now = st.number_input("Тест K", value=10.0)
    base_tds = st.number_input("Поточний TDS", value=150.0)
with col2:
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=3)
    ph = st.number_input("pH", value=6.8)
with col3:
    daily_no3 = st.number_input("Базове споживання NO3", value=consumption_results.get("NO3", 2.0))
    daily_po4 = st.number_input("Базове споживання PO4", value=consumption_results.get("PO4", 0.1))
    daily_k = st.number_input("Базове споживання K", value=consumption_results.get("K", 1.0))

st.subheader("🧪 Щоденне внесення (самоміс)")
d_col1, d_col2, d_col3 = st.columns(3)
c_n, d_ml_n = d_col1.number_input("N г/л", value=50.0), d_col1.number_input("Доза N мл/д", value=0.0)
c_p, d_ml_p = d_col2.number_input("P г/л", value=5.0), d_col2.number_input("Доза P мл/д", value=0.0)
c_k, d_ml_k = d_col3.number_input("K г/л", value=20.0), d_col3.number_input("Доза K мл/д", value=0.0)

# ---------------- 4. ПРОГНОЗ ----------------
st.header("📈 3. Динамічний прогноз")
ratio_now = no3_now / po4_now if po4_now > 0 else 0
stability = 1 / (1 + abs((ratio_now - custom_redfield) / custom_redfield))
adj_n_cons, adj_p_cons, adj_k_cons = daily_no3 * stability, daily_po4 * stability, daily_k * stability

forecast = []
curr_n, curr_p, curr_k = no3_now, po4_now, k_now
for d in range(days + 1):
    forecast.append({"День": d, "NO3": curr_n, "PO4": curr_p, "K": curr_k})
    curr_n = clamp(curr_n + (d_ml_n * c_n / tank_vol) - adj_n_cons, 0, 100)
    curr_p = clamp(curr_p + (d_ml_p * c_p / tank_vol) - adj_p_cons, 0, 15)
    curr_k = clamp(curr_k + (d_ml_k * c_k / tank_vol) - adj_k_cons, 0, 100)

st.line_chart(pd.DataFrame(forecast).set_index("День"))

# ---------------- 5. АНАЛІТИКА ТА ПЛАН ----------------
st.header("📝 4. Експертний висновок")
co2_val = 3 * kh * (10 ** (7 - ph))
k_min = gh * 1.5
f_end = forecast[-1]

col_adv, col_rep = st.columns([1.3, 1])

with col_adv:
    st.subheader("💡 План та Діагноз")
    
    # Редфілд-корекція (миттєва)
    if ratio_now < custom_redfield:
        ml_fix_n = ((po4_now * custom_redfield) - no3_now) * tank_vol / c_n
        st.error(f"⚠️ **Низький Азот:** Для балансу додайте ще **{ml_fix_n:.1f} мл** N одноразово.")
    elif ratio_now > custom_redfield:
        ml_fix_p = ((no3_now / custom_redfield) - po4_now) * tank_vol / c_p
        st.error(f"⚠️ **Низький Фосфор:** Для балансу додайте ще **{ml_fix_p:.1f} мл** P одноразово.")
    
    # Стан Калію
    if curr_k < k_min: st.warning(f"❗ **Дефіцит Калію:** Ризик появи дірок на листках та зупинки метаболізму.")
    elif curr_k > gh * 2.5: st.warning(f"⚠️ **Надлишок Калію:** Може блокувати засвоєння Ca/Mg (радікуліт).")

    # Розрахунок дози на період (щоб вийти на target)
    ml_n_need = get_ml_dose(f_end["NO3"], target_no3, c_n, tank_vol)
    ml_p_need = get_ml_dose(f_end["PO4"], target_po4, c_p, tank_vol)
    ml_k_need = get_ml_dose(f_end["K"], target_k, c_k, tank_vol)

    st.info(f"""**📅 Рекомендована доза на {days} днів (додатково до поточної):**
* **N (Азот):** {ml_n_need/days:.1f} мл/день (Разом: {ml_n_need:.1f})
* **P (Фосфор):** {ml_p_need/days:.1f} мл/день (Разом: {ml_p_need:.1f})
* **K (Калій):** {ml_k_need/days:.1f} мл/день (Разом: {ml_k_need:.1f})""")

with col_rep:
    st.subheader("📋 Звіт для копіювання")
    report = f"""--- AQUA REPORT V8.5 ---
[БАЗОВІ] Об'єм: {tank_vol}л | CO2: {co2_val:.1f} мг/л
[ПАРАМЕТРИ] GH:{gh} | KH:{kh} | pH:{ph} | TDS:{base_tds}
[ТЕСТИ] NO3:{no3_now} | PO4:{po4_now} | K:{k_now}
[МОДЕЛЬ] Redfield:{ratio_now:.1f}:1 | Стабільність:{stability:.2f}
[ПЛАН {days}д] N:+{ml_n_need/days:.1f} мл/д | P:+{ml_p_need/days:.1f} мл/д
-----------------------"""
    st.code(report, language="text")
