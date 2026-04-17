import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V7.8", layout="wide")
st.title("🌿 Toxicode Aquarium System V7.8 Pro")

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
st.caption("Вкажіть дані за минулий період. Калькулятор сам розрахує % підміни на основі вказаних літрів.")

with st.expander("Розгорнути для аналізу минулого періоду"):
    t1, t2, t3 = st.tabs(["Азот (NO3)", "Фосфор (PO4)", "Калій (K)"])
    
    def calc_real_cons(tab, name, key_p):
        with tab:
            c1, c2, c3 = st.columns(3)
            p_test = c1.number_input(f"Тест {name} (початок)", value=15.0, step=0.1, key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=10.0, step=0.1, key=f"c_{key_p}")
            added = c3.number_input(f"Внесено {name} за цей час (мг/л)", value=0.0, step=0.1, key=f"a_{key_p}")
            
            col_low1, col_low2 = st.columns(2)
            ch_liters = col_low1.number_input(f"Літрів підмінено за цей час ({name})", value=0.0, step=1.0, key=f"ch_l_{key_p}")
            d_pass = col_low2.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key_p}")
            
            p_pct = (ch_liters / tank_vol) if tank_vol > 0 else 0
            start_after_wash = p_test * (1 - p_pct)
            res = (start_after_wash + added - c_test) / d_pass
            st.info(f"**Реальне споживання {name}:** {max(res, 0):.2f} мг/л в день (Підміна: {p_pct*100:.1f}%)")

    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

st.divider()

# ---------------- 3. ПОТОЧНІ ПАРАМЕТРИ ----------------
st.header("📋 2. Поточний стан та ввід даних")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Сьогоднішні тести")
    no3 = st.number_input("Поточний NO3", value=10.0, step=1.0)
    po4 = st.number_input("Поточний PO4", value=0.5, step=0.1)
    k = st.number_input("Поточний K", value=10.0, step=1.0)
    base_tds = st.number_input("Поточний TDS", value=150.0, step=5.0)

with col2:
    st.subheader("Параметри води")
    gh = st.number_input("GH", value=6, step=1) #
    kh = st.number_input("KH", value=2, step=1) #
    ph = st.number_input("pH", value=6.8, step=0.1)

with col3:
    st.subheader("Споживання (мг/л/день)")
    daily_no3 = st.number_input("Споживання NO3", value=2.0, step=0.1)
    daily_po4 = st.number_input("Споживання PO4", value=0.1, step=0.1)
    daily_k = st.number_input("Споживання K", value=1.0, step=0.1)

st.divider()

# ---------------- 4. ПІДМІНА ТА ДОЗУВАННЯ ----------------
c_act1, c_act2 = st.columns([1, 2])

with c_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри поточної підміни", value=50.0, step=1.0)
    w_tds = st.number_input("TDS нової води", value=110.0, step=5.0)
    
    current_pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3 = no3 * (1 - current_pct) 
    after_po4 = po4 * (1 - current_pct)
    after_k = k * (1 - current_pct)
    after_tds = base_tds * (1 - current_pct) + (w_tds * current_pct)

with c_act2:
    st.header("🧪 Дозування")
    cd1, cd2, cd3 = st.columns(3)
    c_n = cd1.number_input("N розчин г/л", value=50.0, step=1.0)
    d_n = cd1.number_input("Внести N мл", value=0.0, step=0.1)
    c_p = cd2.number_input("P розчин г/л", value=5.0, step=0.1)
    d_p = cd2.number_input("Внести P мл", value=0.0, step=0.1)
    c_k = cd3.number_input("K розчин г/л", value=20.0, step=1.0)
    d_k = cd3.number_input("Внести K мл", value=0.0, step=0.1)

start_no3 = after_no3 + (d_n * c_n / tank_vol)
start_po4 = after_po4 + (d_p * c_p / tank_vol)
start_k = after_k + (d_k * c_k / tank_vol)

# ---------------- 5. ПРОГНОЗ ----------------
st.header("📈 3. Прогноз динаміки")
forecast = []
for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(start_no3 - daily_no3 * d, 0),
        "PO4": max(start_po4 - daily_po4 * d, 0),
        "K": max(start_k - daily_k * d, 0)
    })
df_f = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_f)

# ---------------- 6. АНАЛІТИКА ----------------
st.header("📊 4. Аналіз параметрів")
res1, res2, res3, res4 = st.columns(4)

co2_calc = 3 * kh * (10**(7 - ph))
ratio_val = start_no3 / start_po4 if start_po4 > 0 else 0
k_limit = gh * 1.5

if co2_calc > co2_limit:
    res1.metric("CO2 (мг/л)", f"{co2_calc:.1f}", "⚠️ НАДЛИШОК", delta_color="inverse")
    st.error(f"🔴 **УВАГА: Високий CO2 ({co2_calc:.1f} мг/л)!**")
else:
    res1.metric("CO2 (мг/л)", f"{co2_calc:.1f}")

res2.metric("Редфілд (N:P)", f"{ratio_val:.1f}:1", f"Ціль {custom_redfield}:1", delta_color="off")
res3.metric("K:GH", f"{start_k:.1f}", f"Мін: {k_limit:.1f}", help="Рівень калію для метаболізму.")
res4.metric("TDS прогноз", f"{after_tds:.0f}")

st.divider()

# ---------------- 7. ПІДСУМОК ----------------
st.header("📝 5. Діагноз та План коригування")
f_no3_end = df_f.iloc[-1]["NO3"]
f_po4_end = df_f.iloc[-1]["PO4"]
f_k_end = df_f.iloc[-1]["K"]

def get_ml_dose(curr, target, conc, vol):
    if curr < target:
        return ((target - curr) * vol) / conc
    return 0.0

# ТУТ БУЛА ПОМИЛКА: додано четвертий аргумент c_k
ml_n_need = get_ml_dose(f_no3_end, target_no3, c_n, tank_vol)
ml_p_need = get_ml_dose(f_po4_end, target_po4, c_p, tank_vol)
ml_k_need = get_ml_dose(f_k_end, target_k, c_k, tank_vol) 

col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader(f"Коригування доз (на {days} дн.)")
    if ml_n_need > 0: st.warning(f"**Азот (N):** Додати {ml_n_need:.1f} мл (або по {ml_n_need/days:.1f} мл/день)")
    if ml_p_need > 0: st.warning(f"**Фосфор (P):** Додати {ml_p_need:.1f} мл (або по {ml_p_need/days:.1f} мл/день)")
    if ml_k_need > 0: st.warning(f"**Калій (K):** Додати {ml_k_need:.1f} мл (або по {ml_k_need/days:.1f} мл/день)")
    if not any([ml_n_need, ml_p_need, ml_k_need]): st.success("Запасів макро достатньо!")

with col_right:
    st.subheader("💡 Висновок")
    diag_msgs = []
    if ratio_val < (custom_redfield - 5): diag_msgs.append("⚠️ Ризик синьо-зелених (низький Редфілд).")
    elif ratio_val > (custom_redfield + 5): diag_msgs.append("⚠️ Ризик ксенококусу (високий Редфілд).")
    if start_k < k_limit: diag_msgs.append("🚫 Калій нижче порогу! Блокується засвоєння азоту.")
    
    if not diag_msgs: st.success("🌟 Система збалансована!")
    else:
        for m in diag_msgs: st.error(m)
