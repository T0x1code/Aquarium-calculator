import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V7.9", layout="wide")
st.title("🌿 Toxicode Aquarium System V7.9 Pro")

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
st.caption("Аналіз минулого періоду з урахуванням підмін.")

with st.expander("Розгорнути для аналізу"):
    t1, t2, t3 = st.tabs(["Азот (NO3)", "Фосфор (PO4)", "Калій (K)"])
    
    # Словник для збереження результатів споживання для звіту
    consumption_results = {}

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
            consumption_results[name] = max(res, 0)
            st.info(f"**Споживання {name}:** {consumption_results[name]:.2f} мг/л в день")

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
    
    curr_pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3 = no3 * (1 - curr_pct) 
    after_po4 = po4 * (1 - curr_pct)
    after_k = k * (1 - curr_pct)
    after_tds = base_tds * (1 - curr_pct) + (w_tds * curr_pct)

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

co2_val = 3 * kh * (10**(7 - ph))
ratio_val = start_no3 / start_po4 if start_po4 > 0 else 0
k_min = gh * 1.5

if co2_val > co2_limit:
    res1.metric("CO2 (мг/л)", f"{co2_val:.1f}", "⚠️ НАДЛИШОК", delta_color="inverse")
else:
    res1.metric("CO2 (мг/л)", f"{co2_val:.1f}")

res2.metric("Редфілд (N:P)", f"{ratio_val:.1f}:1", f"Ціль {custom_redfield}:1")
res3.metric("K:GH", f"{start_k:.1f}", f"Мін: {k_min:.1f}")
res4.metric("TDS прогноз", f"{after_tds:.0f}")

st.divider()

# ---------------- 7. ПІДСУМОК ТА ЗВІТ ----------------
st.header("📝 5. Висновок та План")

f_no3_end = df_f.iloc[-1]["NO3"]
f_po4_end = df_f.iloc[-1]["PO4"]
f_k_end = df_f.iloc[-1]["K"]

def get_ml_dose(curr, target, conc, vol):
    if curr < target:
        return ((target - curr) * vol) / conc
    return 0.0

ml_n_need = get_ml_dose(f_no3_end, target_no3, c_n, tank_vol)
ml_p_need = get_ml_dose(f_po4_end, target_po4, c_p, tank_vol)
ml_k_need = get_ml_dose(f_k_end, target_k, c_k, tank_vol)

# Формування тексту діагнозу
diag_list = []
if ratio_val < (custom_redfield - 5): diag_list.append("⚠️ Низький Редфілд (ризик синьо-зелених)")
elif ratio_val > (custom_redfield + 5): diag_list.append("⚠️ Високий Редфілд (ризик ксенококусу)")
if start_k < k_min: diag_list.append(f"🚫 Дефіцит Калію (менше {k_min:.1f})")
if co2_val > co2_limit: diag_list.append(f"🔴 Критичний CO2 ({co2_val:.1f})")
if not diag_list: diag_list.append("🌟 Система стабільна")

col_res, col_copy = st.columns([1, 1])

with col_res:
    st.subheader("💡 Поради")
    for d in diag_list:
        if "🌟" in d: st.success(d)
        else: st.error(d)
    
    st.write(f"**План на {days} дн.:**")
    st.write(f"- N: {ml_n_need:.1f} мл")
    st.write(f"- P: {ml_p_need:.1f} мл")
    st.write(f"- K: {ml_k_need:.1f} мл")

with col_copy:
    st.subheader("📋 Звіт для копіювання")
    report_text = f"""--- AQUARIUM REPORT ---
ОБ'ЄМ: {tank_vol} л | ПІДМІНА: {change_l} л

[ПАРАМЕТРИ]
NO3: {no3} | PO4: {po4} | K: {k}
GH: {gh} | KH: {kh} | pH: {ph} | TDS: {base_tds}

[АНАЛІТИКА]
CO2: {co2_val:.1f} мг/л (Поріг: {co2_limit})
Редфілд: {ratio_val:.1f}:1 (Ціль: {custom_redfield})
Калій/GH: {start_k:.1f} (Мін: {k_min:.1f})

[СПОЖИВАННЯ (мг/л/день)]
NO3: {consumption_results.get('NO3', 0):.2f} | PO4: {consumption_results.get('PO4', 0):.2f} | K: {consumption_results.get('K', 0):.2f}

[ДІАГНОЗ]
{chr(10).join(diag_list)}

[ПЛАН КОРЕКЦІЇ НА {days} ДНІВ]
Додати N: {ml_n_need:.1f} мл ({ml_n_need/days:.1f} мл/день)
Додати P: {ml_p_need:.1f} мл ({ml_p_need/days:.1f} мл/день)
Додати K: {ml_k_need:.1f} мл ({ml_k_need/days:.1f} мл/день)
-----------------------"""
    st.code(report_text, language="text")
    st.caption("Натисніть на значок копіювання у верхньому правому куті блоку вище.")
