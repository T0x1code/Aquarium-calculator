import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.2", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.2 Stable")

# ---------------- HELPER ----------------
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

# ---------------- 1. SIDEBAR ----------------
with st.sidebar:
    st.header("📏 Конфігурація")

    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)

    st.divider()
    st.subheader("🎯 Цілі")

    target_no3 = st.number_input("Ціль NO3", value=15.0)
    target_po4 = st.number_input("Ціль PO4", value=1.0)
    target_k = st.number_input("Ціль K", value=15.0)

    st.divider()
    st.subheader("⚙️ Аналітика")

    custom_redfield = st.slider("Редфілд (N:1P)", 5, 30, 15)
    days = st.slider("Прогноз (днів)", 1, 14, 7)

    data_quality = st.slider("Якість даних", 0.5, 1.0, 0.85)

# ---------------- 2. СПОЖИВАННЯ ----------------
st.header("📉 Споживання (реальне)")

consumption_results = {}

with st.expander("Аналіз минулого періоду"):

    def calc(tab, name, key):
        with tab:
            c1, c2, c3 = st.columns(3)

            start = c1.number_input(f"{name} старт", value=15.0, key=f"s_{key}")
            end = c2.number_input(f"{name} зараз", value=10.0, key=f"e_{key}")
            added = c3.number_input(f"Внесено", value=0.0, key=f"a_{key}")

            c4, c5 = st.columns(2)
            water_change = c4.number_input("Підміна (л)", value=0.0, key=f"w_{key}")
            days_local = c5.number_input("Днів", value=7, min_value=1, key=f"d_{key}")

            pct = water_change / tank_vol if tank_vol > 0 else 0

            consumption = (start * (1 - pct) + added - end) / days_local
            consumption = max(consumption, 0) * data_quality

            consumption_results[name] = consumption

            st.info(f"{name}: {consumption:.2f} мг/л/д")

    t1, t2, t3 = st.tabs(["NO3", "PO4", "K"])

    calc(t1, "NO3", "no3")
    calc(t2, "PO4", "po4")
    calc(t3, "K", "k")

# ---------------- 3. ПОТОЧНИЙ СТАН ----------------
st.header("📋 Поточний стан")

col1, col2, col3 = st.columns(3)

with col1:
    no3 = st.number_input("NO3", value=10.0)
    po4 = st.number_input("PO4", value=0.5)
    k = st.number_input("K", value=10.0)

with col2:
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=3)
    ph = st.number_input("pH", value=6.8)

with col3:
    daily_no3 = st.number_input("Споживання NO3", value=consumption_results.get("NO3", 2.0))
    daily_po4 = st.number_input("Споживання PO4", value=consumption_results.get("PO4", 0.1))
    daily_k = st.number_input("Споживання K", value=consumption_results.get("K", 1.0))

# стабілізація через Redfield
ratio = no3 / po4 if po4 > 0 else 0
ref_error = (ratio - custom_redfield) / custom_redfield
stability = 1 / (1 + abs(ref_error))

daily_no3 *= stability
daily_po4 *= stability
daily_k *= stability

# ---------------- 4. ПІДМІНА + ДОЗУВАННЯ ----------------
st.header("💧 Підміна та дозування")

change_l = st.number_input("Підміна (л)", value=50.0)
new_tds = st.number_input("TDS нової води", value=110.0)

pct = change_l / tank_vol if tank_vol > 0 else 0

after_no3 = no3 * (1 - pct)
after_po4 = po4 * (1 - pct)
after_k = k * (1 - pct)

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

# ---------------- 5. ПРОГНОЗ ----------------
st.header("📈 Прогноз")

forecast = []
n = start_no3
p = start_po4
k_val = start_k

for d in range(days + 1):

    n = max(n - daily_no3, 0)
    p = max(p - daily_po4, 0)
    k_val = max(k_val - daily_k, 0)

    n = clamp(n, 0, 100)
    p = clamp(p, 0, 10)
    k_val = clamp(k_val, 0, 100)

    forecast.append({
        "День": d,
        "NO3": n,
        "PO4": p,
        "K": k_val
    })

df = pd.DataFrame(forecast)
st.line_chart(df.set_index("День"))

# ---------------- 6. АНАЛІЗ ----------------
st.header("📊 Аналіз")

co2 = 3 * kh * (10 ** (7 - ph))
ratio_final = start_no3 / start_po4 if start_po4 > 0 else 0

st.metric("CO2", f"{co2:.1f}")
st.metric("NO3/PO4", f"{ratio_final:.1f}")

# ---------------- 7. РЕКОМЕНДАЦІЇ ----------------
st.header("🧠 Рекомендації")

f_end = forecast[-1]

def dose(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0

ml_n = dose(f_end["NO3"], target_no3, c_n, tank_vol)
ml_p = dose(f_end["PO4"], target_po4, c_p, tank_vol)
ml_k = dose(f_end["K"], target_k, c_k, tank_vol)

if ref_error < -0.2:
    st.error("Дефіцит азоту (N нижче норми)")
elif ref_error > 0.2:
    st.error("Дефіцит фосфору (P нижче норми)")

st.info(f"""
📅 План на {days} днів:

N: {ml_n:.1f} мл  
P: {ml_p:.1f} мл  
K: {ml_k:.1f} мл  

(стабілізація моделі: {stability:.2f})
""")
start_no3 = after_no3 + (d_n * c_n / tank_vol)
start_po4 = after_po4 + (d_p * c_p / tank_vol)
start_k = after_k + (d_k * c_k / tank_vol)

# ---------------- 5. АНАЛІТИКА ----------------
co2_val = 3 * kh * (10**(7 - ph))
ratio_val = start_no3 / start_po4 if start_po4 > 0 else 0
k_min = gh * 1.5

st.header("📈 3. Прогноз та Аналіз")
forecast = [{"День": d, "NO3": max(start_no3 - daily_no3*d, 0), "PO4": max(start_po4 - daily_po4*d, 0), "K": max(start_k - daily_k*d, 0)} for d in range(days+1)]
st.line_chart(pd.DataFrame(forecast).set_index("День"))

# ---------------- 6. ВИСНОВОК ТА ПЛАН ----------------
st.header("📝 4. Висновок")

def get_ml(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0

f_end = forecast[-1]
ml_n_p = get_ml(f_end["NO3"], target_no3, c_n, tank_vol)
ml_p_p = get_ml(f_end["PO4"], target_po4, c_p, tank_vol)
ml_k_p = get_ml(f_end["K"], target_k, c_k, tank_vol)

col_advice, col_report = st.columns([1.3, 1])

with col_advice:
    # Блок Редфілда
    if ratio_val < custom_redfield:
        ml_fix_n = ((start_po4 * custom_redfield) - start_no3) * tank_vol / c_n
        st.error(f"⚠️ **Дисбаланс Редфілда (Низький Азот):** Додайте **{ml_fix_n:.1f} мл** N для вирівняння.")
    elif ratio_val > custom_redfield:
        ml_fix_p = ((start_no3 / custom_redfield) - start_po4) * tank_vol / c_p
        st.error(f"⚠️ **Дисбаланс Редфілда (Низький Фосфор):** Додайте **{ml_fix_p:.1f} мл** P для вирівняння.")
    
    # Блок Калію
    if start_k < k_min:
        st.warning(f"❗ **Дефіцит Калію ({start_k:.1f} < {k_min:.1f}):** Ризик «дірок» на листках та зупинки росту.")
    elif start_k > gh * 2.5:
        st.warning(f"⚠️ **Надлишок Калію:** Можливе блокування засвоєння Кальцію та Магнію (радікуліт листя).")

    # Щоденна підтримка
    st.info(f"""**📅 План підтримки на {days} днів:**
* **N (Азот):** {ml_n_p/days:.1f} мл/день
* **P (Фосфор):** {ml_p_p/days:.1f} мл/день
* **K (Калій):** {ml_k_p/days:.1f} мл/день

**📦 Сумарно на весь період:**
N: {ml_n_p:.1f} мл | P: {ml_p_p:.1f} мл | K: {ml_k_p:.1f} мл""")

with col_report:
    st.subheader("📋 Звіт для копіювання")
    report = f"""--- AQUA REPORT V8.1 ---
[БАЗОВІ] Об'єм: {tank_vol}л | Підміна: {change_l}л
[ПАРАМЕТРИ] GH:{gh} | KH:{kh} | pH:{ph} | TDS:{after_tds:.0f}
[ТЕСТИ] NO3:{no3} | PO4:{po4} | K:{k} | CO2:{co2_val:.1f}
[БАЛАНС] Редфілд: {ratio_val:.1f}:1 (Ціль {custom_redfield}:1)
[СПОЖИВАННЯ] N:{daily_no3:.2f} | P:{daily_po4:.2f} | K:{daily_k:.2f} (мг/л/д)

[ПЛАН КОРЕКЦІЇ ({days} дн.)]
- N: {ml_n_p/days:.1f} мл/д (Всього: {ml_n_p:.1f})
- P: {ml_p_p/days:.1f} мл/д (Всього: {ml_p_p:.1f})
- K: {ml_k_p/days:.1f} мл/д (Всього: {ml_k_p:.1f})
-----------------------"""
    st.code(report, language="text")
