import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.6", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.6 Stability Engine")

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
    st.subheader("⚙️ Stability Engine Settings")
    custom_redfield = st.slider("Цільовий Редфілд (N:1P)", 5, 30, 15)
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

# ---------------- 3. ПОТОЧНИЙ СТАН ТА МОДЕЛЬ ----------------
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
    daily_no3 = st.number_input("Базове споживання NO3", value=consumption_results.get("NO3", 2.0))
    daily_po4 = st.number_input("Базове споживання PO4", value=consumption_results.get("PO4", 0.1))
    daily_k = st.number_input("Базове споживання K", value=consumption_results.get("K", 1.0))

# Stability Engine Logic
ratio_now = no3_now / po4_now if po4_now > 0 else 0
# Чим далі ми від цілі, тим нижча стабільність (від 0.0 до 1.0)
ref_error = abs((ratio_now - custom_redfield) / custom_redfield)
stability = 1 / (1 + ref_error)

st.divider()
st.subheader("🧪 План внесення (Daily Dosing)")
d_col1, d_col2, d_col3 = st.columns(3)
c_n, d_ml_n = d_col1.number_input("N г/л", value=50.0), d_col1.number_input("Щоденна доза N (мл)", value=0.0)
c_p, d_ml_p = d_col2.number_input("P г/л", value=5.0), d_col2.number_input("Щоденна доза P (мл)", value=0.0)
c_k, d_ml_k = d_col3.number_input("K г/л", value=20.0), d_col3.number_input("Щоденна доза K (мл)", value=0.0)

# ---------------- 4. ДИНАМІЧНИЙ ПРОГНОЗ ----------------
st.header("📈 3. Динамічний прогноз")

forecast = []
curr_n, curr_p, curr_k = no3_now, po4_now, k_now
warns = {"N": None, "P": None, "K": None}

for d in range(days + 1):
    forecast.append({"День": d, "NO3": curr_n, "PO4": curr_p, "K": curr_k})
    
    # Перевірка на виснаження (твій код)
    if warns["N"] is None and curr_n <= 0.1: warns["N"] = d
    if warns["P"] is None and curr_p <= 0.01: warns["P"] = d
    if warns["K"] is None and curr_k <= 0.1: warns["K"] = d

    # Розрахунок змін (Stability Engine впливає на споживання)
    # 1. Додаємо щоденну дозу
    curr_n += (d_ml_n * c_n / tank_vol)
    curr_p += (d_ml_p * c_p / tank_vol)
    curr_k += (d_ml_k * c_k / tank_vol)
    
    # 2. Віднімаємо споживання, скориговане стабільністю
    curr_n -= (daily_no3 * stability)
    curr_p -= (daily_po4 * stability)
    curr_k -= (daily_k * stability)

    curr_n, curr_p, curr_k = clamp(curr_n, 0, 100), clamp(curr_p, 0, 10), clamp(curr_k, 0, 100)

st.line_chart(pd.DataFrame(forecast).set_index("День"))

# Вивід попереджень
if any(warns.values()):
    c_w1, c_w2, c_w3 = st.columns(3)
    if warns["N"]: c_w1.error(f"⚠️ NO3 виснажиться на {warns['N']} день")
    if warns["P"]: c_w2.error(f"⚠️ PO4 виснажиться на {warns['P']} day")
    if warns["K"]: c_w3.warning(f"⚠️ K виснажиться на {warns['K']} день")

# ---------------- 5. АНАЛІЗ ТА РЕКОМЕНДАЦІЇ ----------------
st.header("📊 4. Експертний аналіз")
co2_val = 3 * kh * (10 ** (7 - ph))
k_min = gh * 1.5

col_adv, col_rep = st.columns([1.3, 1])

with col_adv:
    st.subheader("💡 Поради")
    st.write(f"**Stability Engine Score:** `{stability:.2f}`")
    
    if stability < 0.7:
        st.warning("🔄 **Низька стабільність:** Модель прогнозує уповільнення росту рослин через дисбаланс.")
    
    if ratio_now < custom_redfield:
        st.error(f"⚖️ **Дисбаланс:** Мало Азоту. Додайте {( (po4_now*custom_redfield)-no3_now )*tank_vol/c_n:.1f} мл N для вирівняння.")
    elif ratio_now > custom_redfield:
        st.error(f"⚖️ **Дисбаланс:** Мало Фосфору. Додайте {( (no3_now/custom_redfield)-po4_now )*tank_vol/c_p:.1f} мл P для вирівняння.")

    # Розрахунок дози до цілі (Target)
    f_end = forecast[-1]
    ml_n_t = get_ml_dose(f_end["NO3"], target_no3, c_n, tank_vol)
    ml_p_t = get_ml_dose(f_end["PO4"], target_po4, c_p, tank_vol)
    ml_k_t = get_ml_dose(f_end["K"], target_k, c_k, tank_vol)

    st.success(f"""**📦 План корекції (щоб вийти на ціль через {days} дн.):**
* Додатково N: {ml_n_t/days:.1f} мл/день (Разом: {ml_n_t:.1f})
* Додатково P: {ml_p_t/days:.1f} мл/день (Разом: {ml_p_t:.1f})
* Додатково K: {ml_k_t/days:.1f} мл/день (Разом: {ml_k_t:.1f})""")

with col_rep:
    st.subheader("📋 Звіт")
    report = f"""--- AQUA REPORT V8.6 ---
[ПАРАМЕТРИ] GH:{gh} | KH:{kh} | TDS:{base_tds} | CO2:{co2_val:.1f}
[МОДЕЛЬ] Redfield:{ratio_now:.1f}:1 | Stability:{stability:.2f}
[ПРОГНОЗ {days}д] NO3:{f_end['NO3']:.1f} | PO4:{f_end['PO4']:.1f}
-----------------------"""
    st.code(report, language="text")
