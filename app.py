import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Toxicode Aquarium System V11.2", layout="wide")
st.title("🌿 Toxicode Aquarium System V11.2 — Точний акваріумний аналіз")

# ======================== ІНІЦІАЛІЗАЦІЯ СЕСІЇ ========================
if 'history' not in st.session_state:
    st.session_state.history = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# ======================== HELPER FUNCTIONS ========================
def calculate_co2(kh, ph):
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
    """Розрахунок підняття концентрації при внесенні добрива"""
    if volume_l <= 0:
        return 0
    conc_mg_l = conc_g_l * 1000
    return (dose_ml * conc_mg_l) / volume_l

# ======================== SIDEBAR ========================
with st.sidebar:
    st.header("⚙️ Конфігурація")
    tank_vol = st.number_input("Об'єм акваріума (л)", value=200.0, step=10.0, key="tank_vol")
    
    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0, key="target_no3")
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1, key="target_po4")
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0, key="target_k")
    
    st.divider()
    st.subheader("🔬 Фактори коригування")
    efficiency_n = st.slider("Ефективність засвоєння N (%)", 0, 100, 80, key="eff_n")
    efficiency_p = st.slider("Ефективність засвоєння P (%)", 0, 100, 80, key="eff_p")
    efficiency_k = st.slider("Ефективність засвоєння K (%)", 0, 100, 80, key="eff_k")
    
    organic_n_source = st.checkbox("Є органічне джерело N (риби, корм)", value=True, key="organic")
    
    days = st.slider("Період прогнозу (днів)", 1, 30, 7, key="days")

# ======================== 1. РЕМІНЕРАЛІЗАТОР ========================
st.header("💎 1. Ремінералізатор")
with st.expander("Розрахунок солей для підміни", expanded=False):
    col_rem1, col_rem2 = st.columns(2)
    
    with col_rem1:
        c_vol = st.number_input("Літрів осмосу", value=10.0, step=5.0, key="c_vol")
        target_gh = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5, key="target_gh")
        target_kh = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5, key="target_kh")
        target_ca_mg = st.slider("Цільове Ca:Mg", 1.0, 6.0, 3.0, 0.5, key="target_ca_mg")
    
    with col_rem2:
        mg_mgl = target_gh / (target_ca_mg / 5.1 + 1 / 4.3)
        ca_mgl = mg_mgl * target_ca_mg
        
        caco3_g = (target_kh * 17.86 * c_vol / 1000)
        ca_from_caco3_g = caco3_g * 0.4
        
        remaining_ca_g = max(0, (ca_mgl * c_vol / 1000) - ca_from_caco3_g)
        cacl2_g = remaining_ca_g / 0.273 if remaining_ca_g > 0 else 0
        mgso4_g = (mg_mgl * c_vol / 1000) / 0.0986 if mg_mgl > 0 else 0
        
        st.success(f"""
        **Для {c_vol:.0f} л осмосу додай:**
        🧂 **{caco3_g:.3f} г** CaCO₃
        🧂 **{cacl2_g:.3f} г** CaCl₂·2H₂O
        🧂 **{mgso4_g:.3f} г** MgSO₄·7H₂O
        """)

# ======================== 2. РОЗРАХУНОК СПОЖИВАННЯ ========================
st.header("📊 2. Розрахунок реального споживання")

st.info("""
**Як правильно ввести дані:**
1. Вкажіть період між двома тестами (наприклад, 7 днів)
2. Введіть результати першого тесту (на початку періоду)
3. Введіть результати другого тесту (в кінці періоду)
4. Вкажіть **загальний об'єм** добрив, внесених за ВЕСЬ період
5. Вкажіть **загальний об'єм** підміненої води за ВЕСЬ період
""")

col_period, col_wc = st.columns(2)

with col_period:
    days_between = st.number_input("Днів між тестами", min_value=1, max_value=30, value=7, step=1, key="days_between")
    
    st.subheader("📋 Перший тест (початок)")
    no3_start = st.number_input("NO3 (початок)", value=15.0, step=0.5, key="no3_start")
    po4_start = st.number_input("PO4 (початок)", value=1.0, step=0.1, key="po4_start")
    k_start = st.number_input("K (початок)", value=15.0, step=0.5, key="k_start")
    
    st.subheader("📋 Другий тест (кінець)")
    no3_end = st.number_input("NO3 (кінець)", value=10.0, step=0.5, key="no3_end")
    po4_end = st.number_input("PO4 (кінець)", value=0.5, step=0.1, key="po4_end")
    k_end = st.number_input("K (кінець)", value=10.0, step=0.5, key="k_end")

with col_wc:
    st.subheader("💧 Внесені добрива (за весь період)")
    
    dose_n_ml = st.number_input("Внесено N (мл)", value=0.0, step=1.0, key="dose_n_ml")
    conc_n = st.number_input("Концентрація N (г/л)", value=1.0, step=0.5, key="conc_n")
    st.caption(f"→ Підніме NO3 на {dose_to_mgl(dose_n_ml, conc_n, tank_vol):.2f} мг/л")
    
    dose_p_ml = st.number_input("Внесено P (мл)", value=0.0, step=0.5, key="dose_p_ml")
    conc_p = st.number_input("Концентрація P (г/л)", value=0.5, step=0.1, key="conc_p")
    st.caption(f"→ Підніме PO4 на {dose_to_mgl(dose_p_ml, conc_p, tank_vol):.3f} мг/л")
    
    dose_k_ml = st.number_input("Внесено K (мл)", value=0.0, step=1.0, key="dose_k_ml")
    conc_k = st.number_input("Концентрація K (г/л)", value=1.0, step=0.5, key="conc_k")
    st.caption(f"→ Підніме K на {dose_to_mgl(dose_k_ml, conc_k, tank_vol):.2f} мг/л")
    
    st.subheader("💧 Підміна")
    wc_liters = st.number_input("Літрів підмінено за період", value=0.0, step=10.0, key="wc_liters")

# Розрахунок
wc_fraction = wc_liters / tank_vol if tank_vol > 0 else 0

no3_after_wc = no3_start * (1 - wc_fraction)
po4_after_wc = po4_start * (1 - wc_fraction)
k_after_wc = k_start * (1 - wc_fraction)

no3_expected = no3_after_wc + dose_to_mgl(dose_n_ml, conc_n, tank_vol)
po4_expected = po4_after_wc + dose_to_mgl(dose_p_ml, conc_p, tank_vol)
k_expected = k_after_wc + dose_to_mgl(dose_k_ml, conc_k, tank_vol)

consumed_no3 = max(0, no3_expected - no3_end)
consumed_po4 = max(0, po4_expected - po4_end)
consumed_k = max(0, k_expected - k_end)

daily_no3 = consumed_no3 / days_between if days_between > 0 else 0
daily_po4 = consumed_po4 / days_between if days_between > 0 else 0
daily_k = consumed_k / days_between if days_between > 0 else 0

st.divider()
st.subheader("📊 Результат")

col_r1, col_r2, col_r3 = st.columns(3)
with col_r1:
    st.metric("Денне споживання NO3", f"{daily_no3:.2f} мг/л")
    st.caption(f"Очікувано: {no3_expected:.1f} → Факт: {no3_end:.1f}")
with col_r2:
    st.metric("Денне споживання PO4", f"{daily_po4:.3f} мг/л")
    st.caption(f"Очікувано: {po4_expected:.2f} → Факт: {po4_end:.2f}")
with col_r3:
    st.metric("Денне споживання K", f"{daily_k:.2f} мг/л")
    st.caption(f"Очікувано: {k_expected:.1f} → Факт: {k_end:.1f}")

if no3_expected < no3_end:
    st.warning(f"⚠️ Виявлено накопичення NO3! Накопичено: {no3_end - no3_expected:.1f} мг/л")
if po4_expected < po4_end:
    st.warning(f"⚠️ Виявлено накопичення PO4! Накопичено: {po4_end - po4_expected:.2f} мг/л")

# ======================== 3. ПОТОЧНІ ПАРАМЕТРИ ========================
st.header("📋 3. Поточні параметри води")

col1, col2, col3 = st.columns(3)

with col1:
    no3_current = st.number_input("NO3 (мг/л)", value=no3_end, step=0.5, key="no3_current")
    po4_current = st.number_input("PO4 (мг/л)", value=po4_end, step=0.1, key="po4_current")
    k_current = st.number_input("K (мг/л)", value=k_end, step=0.5, key="k_current")
    tds_current = st.number_input("TDS", value=150.0, step=5.0, key="tds_current")

with col2:
    gh = st.number_input("GH (°dH)", value=6, step=1, key="gh")
    kh = st.number_input("KH (°dH)", value=2, step=1, key="kh")
    ph_morning = st.number_input("pH (ранок)", value=7.2, step=0.1, key="ph_morning")
    ph_evening = st.number_input("pH (вечір)", value=6.8, step=0.1, key="ph_evening")
    co2_val = calculate_co2(kh, ph_evening)
    st.metric("Розрахунковий CO₂", f"{co2_val:.1f} мг/л")

with col3:
    use_calculated = st.checkbox("Використати розраховане споживання", value=True, key="use_calculated")
    if use_calculated:
        st.info(f"Споживання: N={daily_no3:.2f}, P={daily_po4:.3f}, K={daily_k:.2f} мг/л/день")
    else:
        daily_no3 = st.number_input("Споживання NO3 (мг/л/день)", value=2.0, step=0.5, key="manual_no3")
        daily_po4 = st.number_input("Споживання PO4 (мг/л/день)", value=0.1, step=0.05, key="manual_po4")
        daily_k = st.number_input("Споживання K (мг/л/день)", value=1.0, step=0.5, key="manual_k")

# ======================== 4. ПЛАНОВА ПІДМІНА ========================
st.divider()
st.header("💧 4. Планова підміна")

planned_wc_l = st.number_input("Літри підміни", value=50.0, step=10.0, key="planned_wc_l")
planned_wc_pct = planned_wc_l / tank_vol if tank_vol > 0 else 0
st.metric("Відсоток підміни", f"{planned_wc_pct*100:.1f}%")

st.subheader("🧪 Добрива ПІСЛЯ підміни (додаються одноразово)")
col_after1, col_after2, col_after3 = st.columns(3)

with col_after1:
    after_n_ml = st.number_input("N мл після підміни", value=0.0, step=1.0, key="after_n_ml")
    after_conc_n = st.number_input("N г/л", value=1.0, step=0.5, key="after_conc_n")
    after_n_add = dose_to_mgl(after_n_ml, after_conc_n, tank_vol)

with col_after2:
    after_p_ml = st.number_input("P мл після підміни", value=0.0, step=0.5, key="after_p_ml")
    after_conc_p = st.number_input("P г/л", value=0.5, step=0.1, key="after_conc_p")
    after_p_add = dose_to_mgl(after_p_ml, after_conc_p, tank_vol)

with col_after3:
    after_k_ml = st.number_input("K мл після підміни", value=0.0, step=1.0, key="after_k_ml")
    after_conc_k = st.number_input("K г/л", value=1.0, step=0.5, key="after_conc_k")
    after_k_add = dose_to_mgl(after_k_ml, after_conc_k, tank_vol)

# ======================== 5. ЩОДЕННЕ ДОЗУВАННЯ ========================
st.header("🧪 5. Щоденне дозування")

col_daily1, col_daily2, col_daily3 = st.columns(3)

with col_daily1:
    daily_n_ml = st.number_input("N мл/день", value=0.0, step=1.0, key="daily_n_ml")
    daily_conc_n = st.number_input("N г/л", value=1.0, step=0.5, key="daily_conc_n")
    daily_n_add = dose_to_mgl(daily_n_ml, daily_conc_n, tank_vol)
    st.caption(f"+{daily_n_add:.2f} мг/л/день")

with col_daily2:
    daily_p_ml = st.number_input("P мл/день", value=0.0, step=0.5, key="daily_p_ml")
    daily_conc_p = st.number_input("P г/л", value=0.5, step=0.1, key="daily_conc_p")
    daily_p_add = dose_to_mgl(daily_p_ml, daily_conc_p, tank_vol)
    st.caption(f"+{daily_p_add:.3f} мг/л/день")

with col_daily3:
    daily_k_ml = st.number_input("K мл/день", value=0.0, step=1.0, key="daily_k_ml")
    daily_conc_k = st.number_input("K г/л", value=1.0, step=0.5, key="daily_conc_k")
    daily_k_add = dose_to_mgl(daily_k_ml, daily_conc_k, tank_vol)
    st.caption(f"+{daily_k_add:.2f} мг/л/день")

# ======================== 6. ФІНАЛЬНИЙ СТАН ПІСЛЯ ПІДМІНИ ========================
after_wc_no3 = no3_current * (1 - planned_wc_pct) + after_n_add
after_wc_po4 = po4_current * (1 - planned_wc_pct) + after_p_add
after_wc_k = k_current * (1 - planned_wc_pct) + after_k_add

st.info(f"**📈 Стан після підміни та одноразового внесення:** NO₃={after_wc_no3:.1f} | PO₄={after_wc_po4:.2f} | K={after_wc_k:.1f}")

# ======================== 7. ПРОГНОЗ ========================
st.header(f"📈 6. Прогноз на {days} днів")

effective_no3 = daily_no3 * (efficiency_n / 100)
effective_po4 = daily_po4 * (efficiency_p / 100)
effective_k = daily_k * (efficiency_k / 100)
organic_n = 0.5 if organic_n_source else 0

forecast = []
curr_n, curr_p, curr_k = after_wc_no3, after_wc_po4, after_wc_k

for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(0, round(curr_n, 1)),
        "PO4": max(0, round(curr_p, 2)),
        "K": max(0, round(curr_k, 1))
    })
    curr_n = max(0, curr_n + daily_n_add - effective_no3 + organic_n)
    curr_p = max(0, curr_p + daily_p_add - effective_po4)
    curr_k = max(0, curr_k + daily_k_add - effective_k)

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)

# ======================== 8. K/GH ========================
st.header("🧂 7. K/GH співвідношення")

k_opt = get_optimal_k_range(gh)
k_ratio = curr_k / gh if gh > 0 else 0

col_k1, col_k2, col_k3 = st.columns(3)
with col_k1:
    st.metric("Поточний K", f"{curr_k:.1f} мг/л")
with col_k2:
    st.metric("K/GH", f"{k_ratio:.2f}", delta="норма 1.5-2.5")
with col_k3:
    if curr_k < k_opt['min']:
        st.error(f"Дефіцит K: +{k_opt['min'] - curr_k:.1f} мг/л")
    elif curr_k <= k_opt['opt_high']:
        st.success("✅ K в нормі")
    else:
        st.warning(f"Надлишок K: -{curr_k - k_opt['opt_high']:.1f} мг/л")

# ======================== 9. КОРЕКЦІЯ ========================
st.divider()
st.header("📅 8. План корекції")

f_end = forecast[-1]

delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4 - f_end["PO4"]
delta_k = target_k - f_end["K"]

st.subheader("Рекомендована зміна добової дози:")

if delta_no3 > 0:
    change_n = (delta_no3 * tank_vol) / (daily_conc_n * days) if daily_conc_n > 0 else 0
    st.metric("N", f"+{change_n:.1f} мл/день", delta=f"до {daily_n_ml + change_n:.1f} мл/день")
elif delta_no3 < 0:
    change_n = (abs(delta_no3) * tank_vol) / (daily_conc_n * days) if daily_conc_n > 0 else 0
    st.metric("N", f"-{change_n:.1f} мл/день", delta=f"до {max(0, daily_n_ml - change_n):.1f} мл/день")
else:
    st.metric("N", "без змін", delta=f"{daily_n_ml:.1f} мл/день")

if delta_po4 > 0:
    change_p = (delta_po4 * tank_vol) / (daily_conc_p * days) if daily_conc_p > 0 else 0
    st.metric("P", f"+{change_p:.2f} мл/день", delta=f"до {daily_p_ml + change_p:.2f} мл/день")
elif delta_po4 < 0:
    change_p = (abs(delta_po4) * tank_vol) / (daily_conc_p * days) if daily_conc_p > 0 else 0
    st.metric("P", f"-{change_p:.2f} мл/день", delta=f"до {max(0, daily_p_ml - change_p):.2f} мл/день")
else:
    st.metric("P", "без змін", delta=f"{daily_p_ml:.2f} мл/день")

if delta_k > 0:
    change_k = (delta_k * tank_vol) / (daily_conc_k * days) if daily_conc_k > 0 else 0
    st.metric("K", f"+{change_k:.1f} мл/день", delta=f"до {daily_k_ml + change_k:.1f} мл/день")
elif delta_k < 0:
    change_k = (abs(delta_k) * tank_vol) / (daily_conc_k * days) if daily_conc_k > 0 else 0
    st.metric("K", f"-{change_k:.1f} мл/день", delta=f"до {max(0, daily_k_ml - change_k):.1f} мл/день")
else:
    st.metric("K", "без змін", delta=f"{daily_k_ml:.1f} мл/день")

st.caption("💡 Змінюйте дозування поступово, не більше ніж на 20% за день")

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
        st.warning(f"CO₂: {co2_val:.1f} мг/л — дефіцит (норма 25-35)")
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

report = f"""=== TOXICODE AQUARIUM V11.2 ===
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

ОСНОВНІ ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {planned_wc_l} л ({planned_wc_pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | CO₂: {co2_val:.1f} мг/л

СПОЖИВАННЯ (мг/л/день)
NO3: {daily_no3:.2f} | PO4: {daily_po4:.3f} | K: {daily_k:.2f}

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ
NO3: {f_end['NO3']:.1f} → {target_no3}
PO4: {f_end['PO4']:.2f} → {target_po4}
K: {f_end['K']:.1f} → {target_k}

РИЗИК ВОДОРОСТЕЙ: {algae_risk}
====================================="""

st.code(report, language="text")

st.caption("⚡ Toxicode V11.2 | Всі елементи мають унікальні ключі | Стабільна версія")
