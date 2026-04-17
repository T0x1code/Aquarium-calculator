import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.8", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.8 Pro")

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
    st.subheader("🎯 Ваші цілі (Target)")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    st.divider()
    st.subheader("⚙️ Аналітика")
    custom_redfield = st.slider("Бажана пропорція Редфілда (N:1P)", 5, 30, 15)
    co2_limit = st.slider("Поріг тривоги CO2 (мг/л)", 20, 100, 35)
    days = st.slider("Період прогнозу (днів)", 1, 14, 7)

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
            res = (p_test * (1 - p_pct) + added - c_test) / d_p
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"**Споживання {name}:** {val:.2f} мг/л в день")

    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

# ---------------- 3. ПОТОЧНИЙ СТАН ----------------
st.header("📋 2. Поточний стан")
col1, col2, col3 = st.columns(3)
with col1:
    no3_now = st.number_input("Поточний NO3", value=10.0, step=1.0)
    po4_now = st.number_input("Поточний PO4", value=0.5, step=0.1)
    k_now = st.number_input("Поточний K", value=10.0, step=1.0)
    base_tds = st.number_input("Поточний TDS", value=150.0, step=5.0)
with col2:
    gh = st.number_input("GH", value=6, step=1)
    kh = st.number_input("KH", value=2, step=1)
    ph = st.number_input("pH", value=6.8, step=0.1)
with col3:
    daily_no3 = st.number_input("Споживання NO3", value=consumption_results.get('NO3', 2.0), step=0.1)
    daily_po4 = st.number_input("Споживання PO4", value=consumption_results.get('PO4', 0.1), step=0.1)
    daily_k = st.number_input("Споживання K", value=consumption_results.get('K', 1.0), step=0.1)

# ---------------- 4. ПІДМІНА ТА ДОЗУВАННЯ ----------------
st.divider()
c_act1, c_act2 = st.columns([1, 2])
with c_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри підміни", value=50.0, step=1.0)
    w_tds = st.number_input("TDS нової води", value=110.0, step=5.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3, after_po4, after_k = no3_now*(1-pct), po4_now*(1-pct), k_now*(1-pct)
    after_tds = base_tds * (1-pct) + (w_tds * pct)
with c_act2:
    st.header("🧪 Дозування")
    cd1, cd2, cd3 = st.columns(3)
    c_n, d_ml_n = cd1.number_input("N г/л", value=50.0), cd1.number_input("Внести N мл (д)", value=0.0)
    c_p, d_ml_p = cd2.number_input("P г/л", value=5.0), cd2.number_input("Внести P мл (д)", value=0.0)
    c_k, d_ml_k = cd3.number_input("K г/л", value=20.0), cd3.number_input("Внести K мл (д)", value=0.0)

# Stability Engine Logic
ratio_now = no3_now / po4_now if po4_now > 0 else 0
stability = 1 / (1 + abs((ratio_now - custom_redfield) / custom_redfield))

# ---------------- 5. ПРОГНОЗ ----------------
st.header("📈 3. Динамічний прогноз")
forecast = []
curr_n, curr_p, curr_k = after_no3, after_po4, after_k

for d in range(days + 1):
    forecast.append({"День": d, "NO3": curr_n, "PO4": curr_p, "K": curr_k})
    # Враховуємо щоденне внесення та скориговане споживання
    curr_n = clamp(curr_n + (d_ml_n * c_n / tank_vol) - (daily_no3 * stability), 0, 100)
    curr_p = clamp(curr_p + (d_ml_p * c_p / tank_vol) - (daily_po4 * stability), 0, 10)
    curr_k = clamp(curr_k + (d_ml_k * c_k / tank_vol) - (daily_k * stability), 0, 100)

st.line_chart(pd.DataFrame(forecast).set_index("День"))

# ---------------- 6. ВИСНОВОК ТА ПОРАДИ ----------------
st.header("📝 4. Експертний висновок")

co2_val = 3 * kh * (10**(7 - ph))
k_gh_ratio = after_k / gh if gh > 0 else 0
f_end = forecast[-1]

col_adv, col_rep = st.columns([1.3, 1])

with col_adv:
    st.subheader("💡 Аналіз та Поради")
    
    # Стан CO2
    if co2_val < 15: st.warning(f"💨 **Мало CO2 ({co2_val:.1f} мг/л):** Рослини будуть голодувати.")
    elif co2_val > co2_limit: st.error(f"🐟 **Небезпека! CO2 ({co2_val:.1f} мг/л):** Ризик для риб.")
    else: st.success(f"✅ CO2 в нормі: {co2_val:.1f} мг/л")

    # Стан Редфілда
    if ratio_now < custom_redfield:
        st.error(f"⚠️ **Низький Азот:** Додайте {((po4_now*custom_redfield)-no3_now)*tank_vol/c_n:.1f} мл N для балансу.")
    elif ratio_now > custom_redfield:
        st.error(f"⚠️ **Низький Фосфор:** Додайте {((no3_now/custom_redfield)-po4_now)*tank_vol/c_p:.1f} мл P для балансу.")

    # Стан Калію та GH
    if k_now < gh * 1.5:
        st.warning(f"❗ **Дефіцит K/GH:** Калій нижче норми (співвідношення {k_gh_ratio:.1f}). Можливі дірки.")
    elif k_now > gh * 2.5:
        st.warning(f"❗ **Надлишок K/GH:** Калій занадто високий, можливий радікуліт.")

    # Розрахунок дози на період
    ml_n_p = get_ml_dose(f_end["NO3"], target_no3, c_n, tank_vol)
    ml_p_p = get_ml_dose(f_end["PO4"], target_po4, c_p, tank_vol)
    ml_k_p = get_ml_dose(f_end["K"], target_k, c_k, tank_vol)

    st.info(f"""**📅 План корекції (додатково до поточної дози):**
* **N:** {ml_n_p/days:.1f} мл/день | **P:** {ml_p_p/days:.1f} мл/день | **K:** {ml_k_p/days:.1f} мл/день""")

with col_report:
    st.subheader("📋 Звіт для копіювання")
    report = f"""--- AQUA REPORT V8.8 ---
[БАЗОВІ] Об'єм: {tank_vol}л | CO2: {co2_val:.1f} мг/л
[ПАРАМЕТРИ] GH:{gh} | KH:{kh} | pH:{ph} | TDS:{after_tds:.0f}
[ТЕСТИ] NO3:{no3_now} | PO4:{po4_now} | K:{k_now}
[БАЛАНС] Редфілд:{ratio_now:.1f}:1 | K/GH:{k_gh_ratio:.1f}
[ПЛАН {days}д] N:+{ml_n_p/days:.1f} мл/д | P:+{ml_p_p/days:.1f} мл/д
-----------------------"""
    st.code(report, language="text")
