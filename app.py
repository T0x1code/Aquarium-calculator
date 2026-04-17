import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V9.4", layout="wide")
st.title("🌿 Toxicode Aquarium System V9.4 — Smart Dosing Control")

# ======================== HELPER FUNCTIONS ========================
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def calculate_co2(kh, ph):
    """CO₂ (мг/л) = 3 * KH * 10^(7-pH)"""
    return 3 * kh * (10 ** (7 - ph))

def redfield_balance(no3, po4, target_ratio):
    if po4 <= 0: return "Немає P", 0
    ratio = no3 / po4
    if ratio < target_ratio * 0.8: return "дефіцит N", ratio
    elif ratio > target_ratio * 1.2: return "дефіцит P", ratio
    return "баланс", ratio

def get_optimal_k_range(gh):
    return {
        'min': gh * 1.2, 'opt_low': gh * 1.5,
        'opt_high': gh * 2.5, 'max': gh * 3.0,
        'target': gh * 1.8
    }

def calculate_cnpk_status(carbon_estimate, no3, po4, k):
    if carbon_estimate > 0:
        c_ratio = carbon_estimate / po4 if po4 > 0 else 999
        c_status = "норма" if 200 < c_ratio < 600 else "дефіцит C" if c_ratio <= 200 else "надлишок C"
    else: c_status = "невідомо"
    
    np_ratio = no3 / po4 if po4 > 0 else 999
    np_status = "дефіцит N" if np_ratio < 10 else "дефіцит P" if np_ratio > 22 else "баланс"
    
    kn_ratio = k / no3 if no3 > 0 else 999
    k_status = "дефіцит K" if kn_ratio < 0.3 else "надлишок K" if kn_ratio > 1.5 else "баланс"
    
    return {'c_status': c_status, 'np_ratio': np_ratio, 'np_status': np_status, 'kn_ratio': kn_ratio, 'k_status': k_status}

# ======================== SIDEBAR — CONFIG ========================
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)
    
    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    
    st.divider()
    st.subheader("⚙️ Розширені")
    custom_redfield = st.slider("Пропорція Редфілда (N:P)", 5, 30, 15)
    days_forecast = st.slider("Період прогнозу/корекції (днів)", 1, 14, 7)

# ======================== 1. СПОЖИВАННЯ ========================
st.header("📉 1. Калькулятор споживання")
cons_results = {}

with st.expander("Аналіз тестів"):
    tabs = st.tabs(["NO3", "PO4", "K"])
    params = [("NO3", 15.0, "no3"), ("PO4", 1.0, "po4"), ("K", 10.0, "k")]
    
    for i, (name, def_val, key) in enumerate(params):
        with tabs[i]:
            c1, c2, c3 = st.columns(3)
            p_t = c1.number_input(f"Тест {name} (старт)", value=def_val, key=f"p_{key}")
            c_t = c2.number_input(f"Тест {name} (зараз)", value=def_val-2, key=f"c_{key}")
            add = c3.number_input(f"Внесено {name} (мг/л)", value=0.0, key=f"a_{key}")
            
            cl1, cl2 = st.columns(2)
            ch_l = cl1.number_input(f"Підмінено (л) для {name}", value=0.0, key=f"ch_l_{key}")
            d_btwn = cl2.number_input(f"Днів між тестами", value=7, min_value=1, key=f"d_{key}")
            
            pct = ch_l / tank_vol if tank_vol > 0 else 0
            # Формула: (Початок з урахуванням підміни + що додали - що залишилось) / дні
            val = ((p_t * (1 - pct)) + add - c_t) / d_btwn
            cons_results[name] = max(val, 0.0)
            st.info(f"Споживання {name}: {cons_results[name]:.3f} мг/л/день")

# ======================== 2. ПОТОЧНІ ПАРАМЕТРИ ========================
st.header("📋 2. Поточний стан")
col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("NO3 зараз", value=10.0)
    po4_now = st.number_input("PO4 зараз", value=0.5)
    k_now = st.number_input("K зараз", value=10.0)

with col2:
    gh = st.number_input("GH (°dH)", value=6)
    kh = st.number_input("KH (°dH)", value=2)
    ph = st.number_input("pH", value=6.8)

with col3:
    daily_no3 = st.number_input("Споживання NO3/день", value=cons_results.get('NO3', 2.0))
    daily_po4 = st.number_input("Споживання PO4/день", value=cons_results.get('PO4', 0.1))
    daily_k = st.number_input("Споживання K/день", value=cons_results.get('K', 1.0))

# ======================== 3. ДОЗУВАННЯ ТА ПРОГНОЗ ========================
st.divider()
cd_n, cd_p, cd_k = st.columns(3)

with cd_n:
    conc_n = st.number_input("N конц. (г/л)", value=50.0)
    cur_dose_n = st.number_input("Доза N (мл/день)", value=0.0)
with cd_p:
    conc_p = st.number_input("P конц. (г/л)", value=5.0)
    cur_dose_p = st.number_input("Доза P (мл/день)", value=0.0)
with cd_k:
    conc_k = st.number_input("K конц. (г/л)", value=20.0)
    cur_dose_k = st.number_input("Доза K (мл/день)", value=0.0)

# Розрахунок прогнозу
forecast = []
c_n, c_p, c_k = no3_now, po4_now, k_now
for d in range(days_forecast + 1):
    forecast.append({"День": d, "NO3": c_n, "PO4": c_p, "K": c_k})
    c_n = clamp(c_n + (cur_dose_n * conc_n / tank_vol) - daily_no3, 0, 50)
    c_p = clamp(c_p + (cur_dose_p * conc_p / tank_vol) - daily_po4, 0, 5)
    c_k = clamp(c_k + (cur_dose_k * conc_k / tank_vol) - daily_k, 0, 50)

st.line_chart(pd.DataFrame(forecast).set_index("День"))

# ======================== 4. ПЛАН КОРЕКЦІЇ (ВИПРАВЛЕНО) ========================
st.header("📅 3. План корекції дозування")

def calculate_smart_dose(current_val, target_val, daily_cons, conc, vol, days):
    """
    Розраховує нову щоденну дозу:
    1. Покриття щоденного споживання
    2. Плавне виведення на ціль (дефіцит розподілений на період)
    """
    if conc <= 0: return 0.0
    # Скільки мг/л потрібно вносити щодня для компенсації споживання
    dose_for_consumption_mg = daily_cons
    # Скільки мг/л потрібно додавати щодня, щоб через 'days' вийти на ціль
    deficit_mg = target_val - current_val
    dose_for_correction_mg = deficit_mg / days
    
    total_needed_mg_daily = dose_for_consumption_mg + dose_for_correction_mg
    # Конвертація мг/л в мл
    new_dose_ml = (total_needed_mg_daily * vol) / conc
    return max(0.0, new_dose_ml)

new_n = calculate_smart_dose(no3_now, target_no3, daily_no3, conc_n, tank_vol, days_forecast)
new_p = calculate_smart_dose(po4_now, target_po4, daily_po4, conc_p, tank_vol, days_forecast)
new_k = calculate_smart_dose(k_now, target_k, daily_k, conc_k, tank_vol, days_forecast)

rec_col1, rec_col2, rec_col3 = st.columns(3)
rec_col1.metric("Нова доза NO3", f"{new_n:.1f} мл/д", f"{new_n - cur_dose_n:.1f}")
rec_col2.metric("Нова доза PO4", f"{new_p:.2f} мл/д", f"{new_p - cur_dose_p:.2f}")
rec_col3.metric("Нова доза K", f"{new_k:.1f} мл/д", f"{new_k - cur_dose_k:.1f}")

st.success(f"Ці дози виведуть акваріум на цільові показники за {days_forecast} днів.")

# ======================== 5. АНАЛІТИКА ТА ЗВІТ ========================
co2_val = calculate_co2(kh, ph)
cnpk = calculate_cnpk_status(co2_val, no3_now, po4_now, k_now)

with st.expander("📊 Аналіз балансу C:N:P:K"):
    st.write(f"**CO2:** {co2_val:.1f} мг/л ({cnpk['c_status']})")
    st.write(f"**N:P Ratio:** {cnpk['np_ratio']:.1f}:1 ({cnpk['np_status']})")
    st.write(f"**K:N Ratio:** {cnpk['kn_ratio']:.2f}:1 ({cnpk['k_status']})")

# Звіт для копіювання
report = f"""=== TOXICODE REPORT V9.4 ===
Параметри: NO3:{no3_now} | PO4:{po4_now} | K:{k_now} | CO2:{co2_val:.1f}
Споживання: N:{daily_no3} | P:{daily_po4} | K:{daily_k}
---
РЕКОМЕНДОВАНІ ДОЗИ (мл/день):
N: {new_n:.1f} (було {cur_dose_n})
P: {new_p:.2f} (було {cur_dose_p})
K: {new_k:.1f} (було {cur_dose_k})
Ціль буде досягнута за {days_forecast} днів.
============================"""
st.code(report)
