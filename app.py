import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Toxicode Aquarium System V11.0", layout="wide")
st.title("🌿 Toxicode Aquarium System V11.0 — Точний акваріумний аналіз")

# ======================== ІНІЦІАЛІЗАЦІЯ СЕСІЇ ========================
if 'history' not in st.session_state:
    st.session_state.history = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# ======================== HELPER FUNCTIONS ========================
def calculate_co2(kh, ph):
    """CO₂ (мг/л) = 3 * KH * 10^(7-pH)"""
    try:
        return 3 * kh * (10 ** (7 - ph))
    except:
        return 0

def get_optimal_k_range(gh):
    return {
        'min': gh * 1.2,
        'opt_low': gh * 1.5,
        'opt_high': gh * 2.5,
        'max': gh * 3.0,
        'target': gh * 1.8
    }

def dose_to_mgl(dose_ml, conc_g_l, volume_l):
    """Перевід мл добрива в мг/л підняття концентрації"""
    if volume_l <= 0:
        return 0
    return (dose_ml * conc_g_l * 1000) / volume_l

# ======================== SIDEBAR ========================
with st.sidebar:
    st.header("⚙️ Конфігурація системи")
    tank_vol = st.number_input("Об'єм акваріума (л)", value=200.0, step=10.0)
    
    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    
    st.divider()
    st.subheader("🔬 Фактори коригування")
    efficiency_n = st.slider("Ефективність засвоєння N (%)", 0, 100, 80, 
                             help="80% означає що 20% добрив не засвоюється або блокується")
    efficiency_p = st.slider("Ефективність засвоєння P (%)", 0, 100, 80)
    efficiency_k = st.slider("Ефективність засвоєння K (%)", 0, 100, 80)
    
    organic_n_source = st.checkbox("Є органічне джерело N (риби, корм)", value=True,
                                   help="Риби та корм виділяють аміак який перетворюється на NO3")
    
    days = st.slider("Період прогнозу (днів)", 1, 30, 7)

# ======================== 1. РЕМІНЕРАЛІЗАТОР ========================
st.header("💎 1. Ремінералізатор")
with st.expander("Розрахунок солей для підміни", expanded=False):
    col_rem1, col_rem2 = st.columns(2)
    
    with col_rem1:
        c_vol = st.number_input("Літрів осмосу", value=10.0, step=5.0)
        target_gh = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5)
        target_kh = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5)
        target_ca_mg = st.slider("Цільове Ca:Mg", 1.0, 6.0, 3.0, 0.5)
    
    with col_rem2:
        # Розрахунок
        mg_mgl = target_gh / (target_ca_mg / 5.1 + 1 / 4.3)
        ca_mgl = mg_mgl * target_ca_mg
        
        caco3_g = (target_kh * 17.86 * c_vol / 1000)
        ca_from_caco3_g = caco3_g * 0.4
        
        remaining_ca_g = max(0, (ca_mgl * c_vol / 1000) - ca_from_caco3_g)
        cacl2_g = remaining_ca_g / 0.273 if remaining_ca_g > 0 else 0
        mgso4_g = (mg_mgl * c_vol / 1000) / 0.0986 if mg_mgl > 0 else 0
        
        predicted_tds = ((caco3_g + cacl2_g + mgso4_g) * 1000) / c_vol
        
        st.success(f"""
        **Для {c_vol:.0f} л осмосу додай:**
        🧂 **{caco3_g:.3f} г** CaCO₃
        🧂 **{cacl2_g:.3f} г** CaCl₂·2H₂O
        🧂 **{mgso4_g:.3f} г** MgSO₄·7H₂O
        """)
        st.caption(f"📊 Прогноз TDS: {predicted_tds:.0f} ppm")

# ======================== 2. ПОТОЧНИЙ СТАН ТА ІСТОРІЯ СПОЖИВАННЯ ========================
st.header("📊 2. Введення даних для розрахунку споживання")

st.info("""
**Як правильно ввести дані:**
1. Виберіть період між двома тестами (наприклад, 7 днів)
2. Введіть результати першого тесту (початок періоду)
3. Введіть результати другого тесту (зараз)
4. Вкажіть скільки добрив ви вносили за цей період (сумарно, не щодня!)
5. Вкажіть скільки літрів води підмінили за цей період
""")

col_period, col_wc = st.columns(2)

with col_period:
    days_between = st.number_input("Днів між тестами", min_value=1, max_value=30, value=7, step=1)
    
    st.subheader("📋 Перший тест (початок періоду)")
    no3_start = st.number_input("NO3 (початок)", value=15.0, step=0.5, key="no3_start")
    po4_start = st.number_input("PO4 (початок)", value=1.0, step=0.1, key="po4_start")
    k_start = st.number_input("K (початок)", value=15.0, step=0.5, key="k_start")
    
    st.subheader("📋 Другий тест (зараз)")
    no3_end = st.number_input("NO3 (зараз)", value=10.0, step=0.5, key="no3_end")
    po4_end = st.number_input("PO4 (зараз)", value=0.5, step=0.1, key="po4_end")
    k_end = st.number_input("K (зараз)", value=10.0, step=0.5, key="k_end")

with col_wc:
    st.subheader("💧 Внесення за період")
    dose_n_ml = st.number_input("Внесено N добрив (мл за весь період)", value=0.0, step=5.0)
    conc_n = st.number_input("Концентрація N (г/л)", value=50.0, step=5.0)
    
    dose_p_ml = st.number_input("Внесено P добрив (мл за весь період)", value=0.0, step=2.0)
    conc_p = st.number_input("Концентрація P (г/л)", value=5.0, step=0.5)
    
    dose_k_ml = st.number_input("Внесено K добрив (мл за весь період)", value=0.0, step=5.0)
    conc_k = st.number_input("Концентрація K (г/л)", value=20.0, step=2.0)
    
    st.subheader("💧 Підміна за період")
    wc_liters = st.number_input("Літрів підмінено за період", value=0.0, step=10.0)

# Розрахунок споживання
wc_fraction = wc_liters / tank_vol if tank_vol > 0 else 0

# Враховуємо що підміна розбавляє концентрацію
no3_after_wc = no3_start * (1 - wc_fraction)
po4_after_wc = po4_start * (1 - wc_fraction)
k_after_wc = k_start * (1 - wc_fraction)

# Враховуємо внесені добрива (переводимо мл в мг/л)
no3_added = dose_to_mgl(dose_n_ml, conc_n, tank_vol)
po4_added = dose_to_mgl(dose_p_ml, conc_p, tank_vol)
k_added = dose_to_mgl(dose_k_ml, conc_k, tank_vol)

# Очікувана концентрація без споживання
expected_no3 = no3_after_wc + no3_added
expected_po4 = po4_after_wc + po4_added
expected_k = k_after_wc + k_added

# Реальне споживання (різниця між очікуваним та фактичним)
consumed_no3 = max(0, expected_no3 - no3_end)
consumed_po4 = max(0, expected_po4 - po4_end)
consumed_k = max(0, expected_k - k_end)

# Денне споживання
daily_cons_no3 = consumed_no3 / days_between if days_between > 0 else 0
daily_cons_po4 = consumed_po4 / days_between if days_between > 0 else 0
daily_cons_k = consumed_k / days_between if days_between > 0 else 0

st.divider()
st.subheader("📊 Результат розрахунку споживання")

col_r1, col_r2, col_r3 = st.columns(3)
with col_r1:
    st.metric("Денне споживання NO3", f"{daily_cons_no3:.2f} мг/л/день")
    st.caption(f"Очікувано: {expected_no3:.1f} → Факт: {no3_end:.1f}")
with col_r2:
    st.metric("Денне споживання PO4", f"{daily_cons_po4:.3f} мг/л/день")
    st.caption(f"Очікувано: {expected_po4:.2f} → Факт: {po4_end:.2f}")
with col_r3:
    st.metric("Денне споживання K", f"{daily_cons_k:.2f} мг/л/день")
    st.caption(f"Очікувано: {expected_k:.1f} → Факт: {k_end:.1f}")

if consumed_no3 < 0 or consumed_po4 < 0 or consumed_k < 0:
    st.warning("⚠️ Виявлено накопичення! Можливі причини: перегодівля риб, повільне засвоєння, або неточні тести.")

# ======================== 3. ПОТОЧНІ ПАРАМЕТРИ ========================
st.header("📋 3. Поточні параметри води")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Макроелементи")
    no3_current = st.number_input("NO3 (мг/л)", value=no3_end, step=0.5, key="no3_cur")
    po4_current = st.number_input("PO4 (мг/л)", value=po4_end, step=0.1, key="po4_cur")
    k_current = st.number_input("K (мг/л)", value=k_end, step=0.5, key="k_cur")
    tds_current = st.number_input("TDS", value=150.0, step=5.0)

with col2:
    st.subheader("Жорсткість")
    gh = st.number_input("GH (°dH)", value=6, step=1)
    kh = st.number_input("KH (°dH)", value=2, step=1)
    
    st.divider()
    st.subheader("🌬️ CO₂")
    ph_morning = st.number_input("pH (ранок)", value=7.2, step=0.1)
    ph_evening = st.number_input("pH (вечір)", value=6.8, step=0.1)
    co2_val = calculate_co2(kh, ph_evening)
    st.metric("Розрахунковий CO₂", f"{co2_val:.1f} мг/л")

with col3:
    st.subheader("Налаштування прогнозу")
    use_calculated_consumption = st.checkbox("Використати розраховане споживання", value=True)
    
    if use_calculated_consumption:
        daily_no3 = daily_cons_no3
        daily_po4 = daily_cons_po4
        daily_k = daily_cons_k
        st.info(f"Споживання: N={daily_no3:.2f}, P={daily_po4:.3f}, K={daily_k:.2f} мг/л/день")
    else:
        daily_no3 = st.number_input("Споживання NO3 (мг/л/день)", value=2.0, step=0.5)
        daily_po4 = st.number_input("Споживання PO4 (мг/л/день)", value=0.1, step=0.05)
        daily_k = st.number_input("Споживання K (мг/л/день)", value=1.0, step=0.5)

# ======================== 4. ПІДМІНА ТА ДОЗУВАННЯ ========================
st.divider()
st.header("💧 4. Планова підміна та дозування")

col_plan1, col_plan2 = st.columns(2)

with col_plan1:
    st.subheader("Планова підміна")
    planned_wc_l = st.number_input("Літри підміни", value=50.0, step=10.0)
    planned_wc_pct = planned_wc_l / tank_vol if tank_vol > 0 else 0
    st.metric("Відсоток підміни", f"{planned_wc_pct*100:.1f}%")

with col_plan2:
    st.subheader("Добрива ПІСЛЯ підміни (на цей об'єм)")
    dose_after_n_ml = st.number_input("N мл після підміни", value=0.0, step=5.0, key="after_n")
    conc_n_after = st.number_input("N г/л", value=50.0, key="conc_n_after")
    add_n_after = dose_to_mgl(dose_after_n_ml, conc_n_after, tank_vol)
    
    dose_after_p_ml = st.number_input("P мл після підміни", value=0.0, step=2.0, key="after_p")
    conc_p_after = st.number_input("P г/л", value=5.0, key="conc_p_after")
    add_p_after = dose_to_mgl(dose_after_p_ml, conc_p_after, tank_vol)
    
    dose_after_k_ml = st.number_input("K мл після підміни", value=0.0, step=5.0, key="after_k")
    conc_k_after = st.number_input("K г/л", value=20.0, key="conc_k_after")
    add_k_after = dose_to_mgl(dose_after_k_ml, conc_k_after, tank_vol)

# ======================== 5. ЩОДЕННЕ ДОЗУВАННЯ ========================
st.header("🧪 5. Щоденне дозування")

col_daily1, col_daily2, col_daily3 = st.columns(3)

with col_daily1:
    daily_dose_n_ml = st.number_input("N мл/день", value=0.0, step=2.0, key="daily_n")
    conc_n_daily = st.number_input("N г/л", value=50.0, key="conc_n_daily")
    daily_add_n = dose_to_mgl(daily_dose_n_ml, conc_n_daily, tank_vol)

with col_daily2:
    daily_dose_p_ml = st.number_input("P мл/день", value=0.0, step=1.0, key="daily_p")
    conc_p_daily = st.number_input("P г/л", value=5.0, key="conc_p_daily")
    daily_add_p = dose_to_mgl(daily_dose_p_ml, conc_p_daily, tank_vol)

with col_daily3:
    daily_dose_k_ml = st.number_input("K мл/день", value=0.0, step=2.0, key="daily_k")
    conc_k_daily = st.number_input("K г/л", value=20.0, key="conc_k_daily")
    daily_add_k = dose_to_mgl(daily_dose_k_ml, conc_k_daily, tank_vol)

# ======================== 6. РОЗРАХУНОК ФІНАЛЬНИХ ЗНАЧЕНЬ ========================
# Після підміни та внесення добрив після підміни
after_wc_no3 = no3_current * (1 - planned_wc_pct) + add_n_after
after_wc_po4 = po4_current * (1 - planned_wc_pct) + add_p_after
after_wc_k = k_current * (1 - planned_wc_pct) + add_k_after

# Враховуємо щоденне дозування (воно додається КОЖНОГО ДНЯ)
# Тому для прогнозу ми будемо додавати його в циклі

st.info(f"**📈 Стан після підміни та внесення:** NO₃={after_wc_no3:.1f} | PO₄={after_wc_po4:.2f} | K={after_wc_k:.1f}")

# ======================== 7. ПРОГНОЗ ========================
st.header(f"📈 6. Прогноз на {days} днів")

# Коригуємо споживання на ефективність
effective_daily_no3 = daily_no3 * (efficiency_n / 100)
effective_daily_po4 = daily_po4 * (efficiency_p / 100)
effective_daily_k = daily_k * (efficiency_k / 100)

# Додаткове джерело N з органіки
organic_n = 0.5 if organic_n_source else 0  # приблизно 0.5 мг/л NO3 на день від риб

forecast = []
curr_n, curr_p, curr_k = after_wc_no3, after_wc_po4, after_wc_k

for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(0, round(curr_n, 1)),
        "PO4": max(0, round(curr_p, 2)),
        "K": max(0, round(curr_k, 1))
    })
    
    # Зміна за день: + добрива - споживання + органіка (тільки для N)
    curr_n = max(0, curr_n + daily_add_n - effective_daily_no3 + organic_n)
    curr_p = max(0, curr_p + daily_add_p - effective_daily_po4)
    curr_k = max(0, curr_k + daily_add_k - effective_daily_k)

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)

# ======================== 8. АНАЛІЗ K/GH ========================
st.header("🧂 7. K/GH співвідношення")

k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = curr_k / gh if gh > 0 else 0

col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Поточний K", f"{curr_k:.1f} мг/л")
with col_k2:
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}", delta="норма 1.5-2.5")
with col_k3:
    if curr_k < k_opt_range['min']:
        st.error(f"🔴 Дефіцит K — потрібно +{k_opt_range['min'] - curr_k:.1f} мг/л")
    elif curr_k <= k_opt_range['opt_high']:
        st.success("✅ K в нормі")
    else:
        st.warning(f"🟡 Надлишок K — знизьте на {curr_k - k_opt_range['opt_high']:.1f} мг/л")

# ======================== 9. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.header("📅 8. План корекції дозування")

f_end = forecast[-1]

delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4 - f_end["PO4"]
delta_k = target_k - f_end["K"]

if delta_no3 > 0:
    change_n = (delta_no3 * tank_vol) / (conc_n_daily * days) if conc_n_daily > 0 else 0
    st.metric("N корекція", f"+{change_n:.1f} мл/день", delta="додати до поточної дози")
elif delta_no3 < 0:
    change_n = (abs(delta_no3) * tank_vol) / (conc_n_daily * days) if conc_n_daily > 0 else 0
    st.metric("N корекція", f"-{change_n:.1f} мл/день", delta="зменшити поточну дозу")
else:
    st.metric("N корекція", "без змін")

if delta_po4 > 0:
    change_p = (delta_po4 * tank_vol) / (conc_p_daily * days) if conc_p_daily > 0 else 0
    st.metric("P корекція", f"+{change_p:.2f} мл/день", delta="додати до поточної дози")
elif delta_po4 < 0:
    change_p = (abs(delta_po4) * tank_vol) / (conc_p_daily * days) if conc_p_daily > 0 else 0
    st.metric("P корекція", f"-{change_p:.2f} мл/день", delta="зменшити поточну дозу")
else:
    st.metric("P корекція", "без змін")

if delta_k > 0:
    change_k = (delta_k * tank_vol) / (conc_k_daily * days) if conc_k_daily > 0 else 0
    st.metric("K корекція", f"+{change_k:.1f} мл/день", delta="додати до поточної дози")
elif delta_k < 0:
    change_k = (abs(delta_k) * tank_vol) / (conc_k_daily * days) if conc_k_daily > 0 else 0
    st.metric("K корекція", f"-{change_k:.1f} мл/день", delta="зменшити поточну дозу")
else:
    st.metric("K корекція", "без змін")

# ======================== 10. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("📝 9. Експертний висновок")

# Оцінка ризику водоростей
if po4_current > 0:
    ratio_np = no3_current / po4_current
    if ratio_np < 10:
        algae_risk = "🔴 Високий (дефіцит N)"
    elif ratio_np > 25:
        algae_risk = "🟠 Високий (дефіцит P)"
    elif no3_current > 30 or po4_current > 1.5:
        algae_risk = "🟡 Середній (надлишок)"
    else:
        algae_risk = "🟢 Низький"
else:
    algae_risk = "Немає даних"

col_exp1, col_exp2 = st.columns(2)

with col_exp1:
    st.write("**Стан системи:**")
    if co2_val < 20:
        st.warning(f"CO₂: {co2_val:.1f} мг/л — дефіцит")
    elif co2_val > 40:
        st.warning(f"CO₂: {co2_val:.1f} мг/л — надлишок")
    else:
        st.success(f"✅ CO₂: {co2_val:.1f} мг/л — норма")
    
    st.write(f"**Ризик водоростей:** {algae_risk}")

with col_exp2:
    st.write(f"**Прогноз через {days} днів:**")
    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л", delta=f"{f_end['NO3'] - target_no3:.1f}")
    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л", delta=f"{f_end['PO4'] - target_po4:.2f}")
    st.metric("K", f"{f_end['K']:.1f} мг/л", delta=f"{f_end['K'] - target_k:.1f}")

# ======================== 11. ЗВІТ ========================
st.divider()
st.subheader("📋 10. Звіт")

report = f"""=== TOXICODE AQUARIUM V11.0 REPORT ===
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

ОСНОВНІ ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {planned_wc_l} л ({planned_wc_pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | CO₂: {co2_val:.1f} мг/л

СПОЖИВАННЯ (мг/л/день)
NO3: {daily_cons_no3:.2f} | PO4: {daily_cons_po4:.3f} | K: {daily_cons_k:.2f}

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ
NO3: {f_end['NO3']:.1f} → {target_no3}
PO4: {f_end['PO4']:.2f} → {target_po4}
K: {f_end['K']:.1f} → {target_k}

РИЗИК ВОДОРОСТЕЙ: {algae_risk}
====================================="""

st.code(report, language="text")

st.caption("⚡ Toxicode V11.0 | Коректне споживання | Органічне джерело N | Ефективність засвоєння")
