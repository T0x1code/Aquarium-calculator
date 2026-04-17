import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.1", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.1 Pro")

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
    no3 = st.number_input("Поточний NO3", value=10.0, step=1.0)
    po4 = st.number_input("Поточний PO4", value=0.5, step=0.1)
    k = st.number_input("Поточний K", value=10.0, step=1.0)
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
    after_no3, after_po4, after_k = no3*(1-pct), po4*(1-pct), k*(1-pct)
    after_tds = base_tds * (1-pct) + (w_tds * pct)
with c_act2:
    st.header("🧪 Дозування")
    cd1, cd2, cd3 = st.columns(3)
    c_n, d_n = cd1.number_input("N г/л", value=50.0, step=1.0), cd1.number_input("Внести N мл", value=0.0, step=0.1)
    c_p, d_p = cd2.number_input("P г/л", value=5.0, step=0.1), cd2.number_input("Внести P мл", value=0.0, step=0.1)
    c_k, d_k = cd3.number_input("K г/л", value=20.0, step=1.0), cd3.number_input("Внести K мл", value=0.0, step=0.1)

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
st.header("📝 4. Експертний висновок")

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
