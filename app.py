import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.0", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.0 Pro")

# ---------------- 1. SIDEBAR: НАЛАШТУВАННЯ ТА ЦІЛІ ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)
    
    st.divider()
    st.subheader("🎯 Ваші цілі (Target)")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    
    st.divider()
    st.subheader("⚙️ Налаштування аналітики")
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
            
            col_low1, col_low2 = st.columns(2)
            ch_l = col_low1.number_input(f"Літрів підмінено ({name})", value=0.0, step=1.0, key=f"ch_l_{key_p}")
            d_p = col_low2.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key_p}")
            
            p_pct = (ch_l / tank_vol) if tank_vol > 0 else 0
            start_after_w = p_test * (1 - p_pct)
            res = (start_after_w + added - c_test) / d_p
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"**Споживання {name}:** {val:.2f} мг/л в день")

    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

st.divider()

# ---------------- 3. ПОТОЧНІ ПАРАМЕТРИ ----------------
st.header("📋 2. Поточний стан")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Сьогоднішні тести")
    no3 = st.number_input("Поточний NO3", value=10.0, step=1.0)
    po4 = st.number_input("Поточний PO4", value=0.5, step=0.1)
    k = st.number_input("Поточний K", value=10.0, step=1.0)
    base_tds = st.number_input("Поточний TDS", value=150.0, step=5.0)

with col2:
    st.subheader("Параметри води")
    gh = st.number_input("GH", value=6, step=1)
    kh = st.number_input("KH", value=2, step=1)
    ph = st.number_input("pH", value=6.8, step=0.1)

with col3:
    st.subheader("Споживання (мг/л/день)")
    daily_no3 = st.number_input("Споживання NO3", value=consumption_results.get('NO3', 2.0), step=0.1)
    daily_po4 = st.number_input("Споживання PO4", value=consumption_results.get('PO4', 0.1), step=0.1)
    daily_k = st.number_input("Споживання K", value=consumption_results.get('K', 1.0), step=0.1)

# ---------------- 4. ПІДМІНА ТА ДОЗУВАННЯ ----------------
c_act1, c_act2 = st.columns([1, 2])
with c_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри поточної підміни", value=50.0, step=1.0)
    w_tds = st.number_input("TDS нової води", value=110.0, step=5.0)
    
    curr_pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3, after_po4, after_k = no3*(1-curr_pct), po4*(1-curr_pct), k*(1-curr_pct)
    after_tds = base_tds * (1-curr_pct) + (w_tds * curr_pct)

with c_act2:
    st.header("🧪 Дозування")
    cd1, cd2, cd3 = st.columns(3)
    c_n, d_n = cd1.number_input("N розчин г/л", value=50.0, step=1.0), cd1.number_input("Внести N мл", value=0.0, step=0.1)
    c_p, d_p = cd2.number_input("P розчин г/л", value=5.0, step=0.1), cd2.number_input("Внести P мл", value=0.0, step=0.1)
    c_k, d_k = cd3.number_input("K розчин г/л", value=20.0, step=1.0), cd3.number_input("Внести K мл", value=0.0, step=0.1)

# Стан ПІСЛЯ внесення добрив
start_no3 = after_no3 + (d_n * c_n / tank_vol)
start_po4 = after_po4 + (d_p * c_p / tank_vol)
start_k = after_k + (d_k * c_k / tank_vol)

# ---------------- 5. ПРОГНОЗ ТА АНАЛІТИКА ----------------
st.header("📊 3. Аналіз та Прогноз")
co2_val = 3 * kh * (10**(7 - ph))
ratio_val = start_no3 / start_po4 if start_po4 > 0 else 0
k_min = gh * 1.5

forecast = [{"День": d, "NO3": max(start_no3 - daily_no3*d, 0), "PO4": max(start_po4 - daily_po4*d, 0), "K": max(start_k - daily_k*d, 0)} for d in range(days+1)]
st.line_chart(pd.DataFrame(forecast).set_index("День"))

res1, res2, res3, res4 = st.columns(4)
res1.metric("CO2 (мг/л)", f"{co2_val:.1f}", "⚠️" if co2_val > co2_limit else "")
res2.metric("Редфілд (N:P)", f"{ratio_val:.1f}:1", f"Ціль {custom_redfield}:1")
res3.metric("K:GH", f"{start_k:.1f}", f"Мін: {k_min:.1f}")
res4.metric("TDS", f"{after_tds:.0f}")

st.divider()

# ---------------- 6. ВИСНОВОК ТА ПЛАН ----------------
st.header("📝 4. Експертний висновок")

def get_ml(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0

# Розрахунок дефіциту за період
f_end = forecast[-1]
ml_n_p = get_ml(f_end["NO3"], target_no3, c_n, tank_vol)
ml_p_p = get_ml(f_end["PO4"], target_po4, c_p, tank_vol)
ml_k_p = get_ml(f_end["K"], target_k, c_k, tank_vol)

col_advice, col_report = st.columns([1.2, 1])

with col_advice:
    st.subheader("💡 План дій")
    
    # Секція Редфілд-корекції
    if ratio_val < custom_redfield:
        needed_no3 = (start_po4 * custom_redfield) - start_no3
        ml_fix_n = (needed_no3 * tank_vol) / c_n
        st.error(f"⚠️ **Низький Азот:** Для балансу {custom_redfield}:1 додайте ще **{ml_fix_n:.1f} мл** розчину N.")
    elif ratio_val > custom_redfield:
        needed_po4 = (start_no3 / custom_redfield) - start_po4
        ml_fix_p = (needed_po4 * tank_vol) / c_p
        st.error(f"⚠️ **Низький Фосфор:** Для балансу {custom_redfield}:1 додайте ще **{ml_fix_p:.1f} мл** розчину P.")
    else:
        st.success("✅ Пропорція Редфілда в ідеальному балансі!")

    # Секція Калію та CO2
    if start_k < k_min: st.warning(f"❗ **Дефіцит Калію:** Додайте {(k_min - start_k)*tank_vol/c_k:.1f} мл для метаболізму.")
    if co2_val > co2_limit: st.error(f"🔴 **Ризик задухи!** CO2 ({co2_val:.1f}) перевищує ваш поріг.")

    st.info(f"""**Щоденна підтримка (на {days} днів):**
- **N (Азот):** {ml_n_p/days:.1f} мл/день
- **P (Фосфор):** {ml_p_p/days:.1f} мл/день
- **K (Калій):** {ml_k_p/days:.1f} мл/день
*(Всього за період: N:{ml_n_p:.1f}, P:{ml_p_p:.1f}, K:{ml_k_p:.1f} мл)*""")

with col_report:
    st.subheader("📋 Звіт для копіювання")
    diag_summary = "Баланс OK" if abs(ratio_val - custom_redfield) < 2 else ("Низький N" if ratio_val < custom_redfield else "Низький P")
    report = f"""--- AQUA REPORT V8.0 ---
ПАРАМЕТРИ: NO3:{no3} | PO4:{po4} | K:{k} | CO2:{co2_val:.1f}
РЕДФІЛД: {ratio_val:.1f}:1 (Ціль {custom_redfield}:1) | СТАН: {diag_summary}

ПЛАН КОРЕКЦІЇ (на {days} дн.):
- N: {ml_n_p/days:.1f} мл/день (всього {ml_n_p:.1f})
- P: {ml_p_p/days:.1f} мл/день (всього {ml_p_p:.1f})
- K: {ml_k_p/days:.1f} мл/день (всього {ml_k_p:.1f})

ПОРАДА: {"Додати N" if ratio_val < custom_redfield else "Додати P" if ratio_val > custom_redfield else "Тримати норму"}
-----------------------"""
    st.code(report, language="text")
