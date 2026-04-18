import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V9.6", layout="wide")
st.title("🌿 Toxicode Aquarium System V9.6 — Професійний контроль")

# ======================== HELPER FUNCTIONS ========================
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def calculate_co2(kh, ph):
    """CO₂ (мг/л) = 3 * KH * 10^(7-pH)"""
    return 3 * kh * (10 ** (7 - ph))

def redfield_balance(no3, po4, target_ratio):
    """Оцінка балансу N:P"""
    if po4 <= 0:
        return "Немає P", 0
    ratio = no3 / po4
    if ratio < target_ratio * 0.8:
        return "дефіцит N", ratio
    elif ratio > target_ratio * 1.2:
        return "дефіцит P", ratio
    return "баланс", ratio

def get_optimal_k_range(gh):
    """Повертає мінімум, оптимум, максимум K в мг/л для заданого GH"""
    return {
        'min': gh * 1.2,
        'opt_low': gh * 1.5,
        'opt_high': gh * 2.5,
        'max': gh * 3.0,
        'target': gh * 1.8
    }

def calculate_steady_state(daily_dose, weekly_change_pct):
    """Розрахунок рівноважної концентрації"""
    if weekly_change_pct <= 0:
        return daily_dose * 365
    return (daily_dose * 7) / weekly_change_pct

# ======================== SIDEBAR ========================
with st.sidebar:
    st.header("Конфігурація системи")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)
    
    st.divider()
    st.subheader("Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    target_tds = st.number_input("Ціль TDS", value=120.0, step=5.0)
    
    st.divider()
    st.subheader("Розширені налаштування")
    custom_redfield = st.slider("Бажана пропорція Редфілда (N:P)", 5, 30, 15)
    co2_min_opt = st.slider("Нижня межа CO₂ (мг/л)", 0, 100, 25)
    co2_max_opt = st.slider("Верхня межа CO₂ (мг/л)", 0, 100, 45)
    days = st.slider("Період прогнозу (днів)", 1, 14, 7)

# ======================== 1. РЕМІНЕРАЛІЗАТОР ========================
st.header("1. Ремінералізатор")
with st.expander("Розрахунок солей для підміни", expanded=True):
    c_vol = st.number_input("Літрів свіжої води (осмос)", value=10.0, step=5.0)
    
    target_gh = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5)
    target_kh = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5)
    target_ca_mg_ratio = st.slider("Цільове співвідношення Ca:Mg", 1.0, 6.0, 3.0, 0.5)
    
    if target_ca_mg_ratio > 0:
        ratio_factor = target_ca_mg_ratio / 5.1 + 1 / 4.3
        mg_mgl = target_gh / ratio_factor if ratio_factor > 0 else 0
        ca_mgl = target_ca_mg_ratio * mg_mgl
    else:
        ca_mgl = target_gh * 5.1
        mg_mgl = 0
    
    total_ca_g = ca_mgl * c_vol / 1000
    total_mg_g = mg_mgl * c_vol / 1000
    
    kh_from_caco3 = (target_kh * 17.86 * c_vol / 1000)
    ca_from_caco3_g = kh_from_caco3 * 0.4
    
    remaining_ca_g = max(0, total_ca_g - ca_from_caco3_g)
    cacl2_g = remaining_ca_g / 0.273 if remaining_ca_g > 0 else 0
    mgso4_g = total_mg_g / 0.0986 if total_mg_g > 0 else 0
    
    st.success(f"""
    **Для {c_vol:.0f} л осмосу додай:**
    🧂 **{kh_from_caco3:.3f} г** CaCO₃
    🧂 **{cacl2_g:.3f} г** CaCl₂·2H₂O
    🧂 **{mgso4_g:.3f} г** MgSO₄·7H₂O
    """)

# ======================== 2. КАЛЬКУЛЯТОР СПОЖИВАННЯ ========================
st.header("2. Калькулятор реального споживання")
consumption_results = {}

with st.expander("Аналіз минулого періоду"):
    t1, t2, t3 = st.tabs(["NO3", "PO4", "K"])
    
    def calc_real_cons(tab, name, key_p):
        with tab:
            c1, c2, c3 = st.columns(3)
            p_test = c1.number_input(f"Тест {name} (початок)", value=15.0, step=0.5, key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=10.0, step=0.5, key=f"c_{key_p}")
            added = c3.number_input(f"Внесено {name} (мг/л)", value=0.0, step=0.5, key=f"a_{key_p}")
            
            cl1, cl2 = st.columns(2)
            ch_l = cl1.number_input(f"Літрів підмінено", value=0.0, step=5.0, key=f"ch_l_{key_p}")
            days_between = cl2.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key_p}")
            
            pct_wc = (ch_l / tank_vol) if tank_vol > 0 else 0
            res = (p_test * (1 - pct_wc) + added - c_test) / days_between
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"Споживання {name}: {val:.2f} мг/л в день")
    
    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

# ======================== 3. ПОТОЧНИЙ СТАН ========================
st.header("3. Поточні параметри води")
col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("NO3 (мг/л)", value=10.0, step=0.5)
    po4_now = st.number_input("PO4 (мг/л)", value=0.5, step=0.05)
    k_now = st.number_input("K (мг/л)", value=10.0, step=0.5)
    base_tds = st.number_input("TDS", value=150.0, step=5.0)

with col2:
    gh = st.number_input("GH (°dH)", value=6, step=1)
    kh = st.number_input("KH (°dH)", value=2, step=1)
    ph_morning = st.number_input("pH (ранок)", value=7.2, step=0.1)
    ph_evening = st.number_input("pH (вечір)", value=6.8, step=0.1)
    co2_val = calculate_co2(kh, ph_evening)
    st.metric("CO₂", f"{co2_val:.1f} мг/л")

with col3:
    default_no3_cons = consumption_results.get('NO3', 2.0)
    default_po4_cons = consumption_results.get('PO4', 0.1)
    default_k_cons = consumption_results.get('K', 1.0)
    
    daily_no3 = st.number_input("Споживання NO3", value=default_no3_cons, step=0.1)
    daily_po4 = st.number_input("Споживання PO4", value=default_po4_cons, step=0.05)
    daily_k = st.number_input("Споживання K", value=default_k_cons, step=0.1)

# ======================== 4. ПІДМІНА ВОДИ ========================
st.divider()
st.header("4. Підміна води")

change_l = st.number_input("Літри підміни", value=50.0, step=1.0)
pct = change_l / tank_vol if tank_vol > 0 else 0
st.metric("Відсоток підміни", f"{pct*100:.1f}%")

water_no3 = st.number_input("NO3 у новій воді", value=0.0, step=0.5)
water_po4 = st.number_input("PO4 у новій воді", value=0.0, step=0.1)
water_k = st.number_input("K у новій воді", value=0.0, step=1.0)
water_tds = st.number_input("TDS нової води", value=110.0, step=5.0)

after_no3 = no3_now * (1 - pct) + water_no3 * pct
after_po4 = po4_now * (1 - pct) + water_po4 * pct
after_k = k_now * (1 - pct) + water_k * pct
after_tds = base_tds * (1 - pct) + water_tds * pct

# ======================== 5. ДОЗУВАННЯ ДОБРИВ ========================
st.header("5. Дозування добрив")

col_n, col_p, col_k = st.columns(3)

with col_n:
    conc_n = st.number_input("N (NO3) г/л", value=50.0, step=5.0)
    current_dose_n_ml = st.number_input("Поточна доза N мл/день", value=0.0, step=1.0)
    add_no3 = (current_dose_n_ml * conc_n) / tank_vol

with col_p:
    conc_p = st.number_input("P (PO4) г/л", value=5.0, step=0.5)
    current_dose_p_ml = st.number_input("Поточна доза P мл/день", value=0.0, step=0.5)
    add_po4 = (current_dose_p_ml * conc_p) / tank_vol

with col_k:
    conc_k = st.number_input("K г/л", value=20.0, step=2.0)
    current_dose_k_ml = st.number_input("Поточна доза K мл/день", value=0.0, step=1.0)
    add_k = (current_dose_k_ml * conc_k) / tank_vol

final_no3 = after_no3 + add_no3
final_po4 = after_po4 + add_po4
final_k = after_k + add_k
final_tds = after_tds + (add_no3 + add_po4 + add_k) * 0.5

# ======================== 6. ПРОГНОЗ ========================
st.header(f"6. Динамічний прогноз на {days} днів")

if final_po4 > 0 and custom_redfield > 0:
    current_ratio = final_no3 / final_po4
    stability = 1 / (1 + abs((current_ratio - custom_redfield) / custom_redfield))
else:
    stability = 0.5

forecast = []
curr_n, curr_p, curr_k = final_no3, final_po4, final_k

for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(0, round(curr_n, 1)),
        "PO4": max(0, round(curr_p, 2)),
        "K": max(0, round(curr_k, 1))
    })
    curr_n = max(0, curr_n + add_no3 - (daily_no3 * stability))
    curr_p = max(0, curr_p + add_po4 - (daily_po4 * stability))
    curr_k = max(0, curr_k + add_k - (daily_k * stability))

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)

# ======================== 7. K/GH АНАЛІЗ ========================
st.header("7. K/GH співвідношення")

k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("Як розрахувати цільовий K за GH"):
    st.markdown(f"""
    **Для вашого GH = {gh} °dH:**
    - Мінімум K: {k_opt_range['min']:.1f} мг/л
    - Оптимум K: {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f} мг/л
    - Максимум K: {k_opt_range['max']:.1f} мг/л
    """)

col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Поточний K", f"{final_k:.1f} мг/л")
with col_k2:
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}")
with col_k3:
    if final_k < k_opt_range['min']:
        st.error(f"КРИТИЧНИЙ ДЕФІЦИТ K")
    elif final_k < k_opt_range['opt_low']:
        st.warning(f"Дефіцит K")
    elif final_k <= k_opt_range['opt_high']:
        st.success("✅ K в нормі")
    elif final_k <= k_opt_range['max']:
        st.warning(f"Надлишок K")
    else:
        st.error(f"КРИТИЧНИЙ НАДЛИШОК K")

# ======================== 8. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("8. Експертний висновок")

redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
    st.subheader("Стан системи")
    
    if co2_val < co2_min_opt:
        st.warning(f"CO₂: {co2_val:.1f} мг/л — дефіцит")
    elif co2_val > co2_max_opt:
        st.error(f"CO₂: {co2_val:.1f} мг/л — надлишок")
    else:
        st.success(f"✅ CO₂: {co2_val:.1f} мг/л — норма")
    
    if redfield_status == "дефіцит N":
        st.warning(f"N:P = {redfield_ratio:.1f}:1 — дефіцит азоту")
    elif redfield_status == "дефіцит P":
        st.warning(f"N:P = {redfield_ratio:.1f}:1 — дефіцит фосфору")
    else:
        st.success(f"✅ N:P = {redfield_ratio:.1f}:1 — баланс")

with col_summary2:
    st.subheader(f"Прогноз через {days} днів")
    f_end = forecast[-1]
    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л")
    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л")
    st.metric("K", f"{f_end['K']:.1f} мг/л")

# ======================== 9. ЗВІТ ========================
st.divider()
st.subheader("9. Звіт для журналу")

report = f"""=== TOXICODE AQUARIUM V9.6 REPORT ===
📅 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

ОСНОВНІ ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | TDS: {final_tds:.0f}
CO₂: {co2_val:.1f} мг/л

МАКРО
NO3: {final_no3:.1f} / {target_no3}
PO4: {final_po4:.2f} / {target_po4}
K: {final_k:.1f} / {target_k}

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ
NO3: {f_end['NO3']:.1f}
PO4: {f_end['PO4']:.2f}
K: {f_end['K']:.1f}
====================================="""

st.code(report, language="text")

st.caption("⚡ Toxicode V9.6 | Стабільна версія")
