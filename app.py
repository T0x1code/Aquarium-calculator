import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.7", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.7 Stability Hybrid")

# ---------------- HELPER ----------------
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def get_ml_dose(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0.0

# ---------------- 1. SIDEBAR (Твій інтерфейс) ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)
    st.divider()
    st.subheader("🎯 Ваші цілі (Target)")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    st.divider()
    st.subheader("⚙️ Stability Engine")
    custom_redfield = st.slider("Пропорція Редфілда (N:1P)", 5, 30, 15)
    days = st.slider("Період прогнозу (днів)", 1, 21, 7)
    data_quality = st.slider("Якість даних", 0.5, 1.0, 0.85)

# ---------------- 2. КАЛЬКУЛЯТОР СПОЖИВАННЯ ----------------
st.header("📉 1. Калькулятор реального споживання")
consumption_results = {}

with st.expander("Аналіз минулого періоду"):
    t1, t2, t3 = st.tabs(["Азот (NO3)", "Фосфор (PO4)", "Калій (K)"])
    def calc_real_cons(tab, name, key_p):
        with tab:
            c1, c2, c3 = st.columns(3)
            p_test = c1.number_input(f"Тест {name} (початок)", value=15.0, step=0.1, key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=10.0, step=0.1, key=f"c_{key_p}")
            added = c3.number_input(f"Внесено {name} (мг/л)", value=0.0, step=0.1, key=f"a_{key_p}")
            cl1, cl2 = st.columns(2)
            ch_l = cl1.number_input(f"Літрів підмінено ({name})", value=0.0, step=1.0, key=f"ch_l_{key_p}")
            d_p = cl2.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key_p}")
            p_pct = (ch_l / tank_vol) if tank_vol > 0 else 0
            res = ((p_test * (1 - p_pct) + added - c_test) / d_p) * data_quality
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"**Споживання {name}:** {val:.2f} мг/л/д")

    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

# ---------------- 3. ПОТОЧНИЙ СТАН ----------------
st.header("📋 2. Поточний стан")
col1, col2, col3 = st.columns(3)
with col1:
    no3 = st.number_input("Поточний NO3", value=10.0, step=1.0)
    po4 = st.number_input("Поточний PO4", value=0.5, step=0.1)
    k = st.number_input("Поточний K", value=10.0, step=1.0)
    base_tds = st.number_input("Поточний TDS", value=150.0, step=5.0)
with col2:
    gh = st.number_input("GH", value=6, step=1)
    kh = st.number_input("KH", value=2, step=1)
    ph = st.number_input("pH", value=6.8, step=0.1)
with col3:
    daily_no3 = st.number_input("Базове NO3 (д)", value=consumption_results.get('NO3', 2.0))
    daily_po4 = st.number_input("Базове PO4 (д)", value=consumption_results.get('PO4', 0.1))
    daily_k = st.number_input("Базове K (д)", value=consumption_results.get('K', 1.0))

# Stability Engine: Розрахунок стабільності на старті
ratio_now = no3 / po4 if po4 > 0 else 0
stability = 1 / (1 + abs((ratio_now - custom_redfield) / custom_redfield))

# ---------------- 4. ПІДМІНА ТА ДОЗУВАННЯ ----------------
st.divider()
c_act1, c_act2 = st.columns([1, 2])
with c_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри підміни", value=50.0)
    w_tds = st.number_input("TDS нової води", value=110.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3, after_po4, after_k = no3*(1-pct), po4*(1-pct), k*(1-pct)
    after_tds = base_tds * (1-pct) + (w_tds * pct)
with c_act2:
    st.header("🧪 Дозування (Щоденне)")
    cd1, cd2, cd3 = st.columns(3)
    c_n, d_ml_n = cd1.number_input("N г/л", value=50.0), cd1.number_input("N мл/день", value=0.0)
    c_p, d_ml_p = cd2.number_input("P г/л", value=5.0), cd2.number_input("P мл/день", value=0.0)
    c_k, d_ml_k = cd3.number_input("K г/л", value=20.0), cd3.number_input("K мл/день", value=0.0)

# ---------------- 5. ДИНАМІЧНИЙ ПРОГНОЗ ----------------
st.header("📈 3. Динамічний прогноз")
forecast = []
curr_n, curr_p, curr_k = after_no3, after_po4, after_k
warns = {"N": None, "P": None}

for d in range(days + 1):
    forecast.append({"День": d, "NO3": curr_n, "PO4": curr_p, "K": curr_k})
    if warns["N"] is None and curr_n <= 0.1: warns["N"] = d
    if warns["P"] is None and curr_p <= 0.01: warns["P"] = d

    # Математика: + Внесення - (Споживання * Стабільність)
    curr_n = clamp(curr_n + (d_ml_n * c_n / tank_vol) - (daily_no3 * stability), 0, 100)
    curr_p = clamp(curr_p + (d_ml_p * c_p / tank_vol) - (daily_po4 * stability), 0, 10)
    curr_k = clamp(curr_k + (d_ml_k * c_k / tank_vol) - (daily_k * stability), 0, 100)

st.line_chart(pd.DataFrame(forecast).set_index("День"))

if warns["N"]: st.error(f"🚨 NO3 закінчиться на {warns['N']} день!")
if warns["P"]: st.error(f"🚨 PO4 закінчиться на {warns['P']} день!")

# ---------------- 6. ВИСНОВОК ТА ПЛАН ----------------
st.header("📝 4. Експертний висновок")
co2_val = 3 * kh * (10**(7 - ph))
f_end = forecast[-1]
ml_n_p = get_ml_dose(f_end["NO3"], target_no3, c_n, tank_vol)
ml_p_p = get_ml_dose(f_end["PO4"], target_po4, c_p, tank_vol)
ml_k_p = get_ml_dose(f_end["K"], target_k, c_k, tank_vol)

col_advice, col_report = st.columns([1.3, 1])

with col_advice:
    st.write(f"**Stability Engine Score:** `{stability:.2f}`")
    if ratio_now < custom_redfield:
        st.error(f"⚠️ **Низький Азот:** Додайте {((po4*custom_redfield)-no3)*tank_vol/c_n:.1f} мл N.")
    
    st.info(f"""**📅 План корекції (додатково на {days} дн.):**
* **N:** {ml_n_p/days:.1f} мл/день | **P:** {ml_p_p/days:.1f} мл/день | **K:** {ml_k_p/days:.1f} мл/день""")

with col_report:
    st.subheader("📋 Звіт для копіювання")
    report = f"""--- AQUA REPORT V8.7 ---
[ПАРАМЕТРИ] GH:{gh} | KH:{kh} | pH:{ph} | TDS:{after_tds:.0f} | CO2:{co2_val:.1f}
[МОДЕЛЬ] Redfield:{ratio_now:.1f}:1 | Stability:{stability:.2f}
[СПОЖИВАННЯ] N:{daily_no3*stability:.2f} | P:{daily_po4*stability:.2f} (скориговано)
[ПЛАН {days}д] N:+{ml_n_p/days:.1f} мл/д | P:+{ml_p_p/days:.1f} мл/д
-----------------------"""
    st.code(report, language="text")
