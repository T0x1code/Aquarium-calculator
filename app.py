import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Toxicode Aquarium System V11", layout="wide")
st.title("🌿 Toxicode Aquarium System V11 — Штучний Інтелект Акваріуміста")

# ======================== ІНІЦІАЛІЗАЦІЯ СЕСІЇ ========================
if 'history' not in st.session_state:
    st.session_state.history = []
if 'last_params' not in st.session_state:
    st.session_state.last_params = None
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# ======================== HELPER FUNCTIONS ========================
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def calculate_co2(kh, ph):
    """CO₂ (мг/л) = 3 * KH * 10^(7-pH)"""
    try:
        return 3 * kh * (10 ** (7 - ph))
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0

def redfield_balance(no3, po4, target_ratio):
    if po4 <= 0:
        return "Немає P", 0
    ratio = no3 / po4
    if ratio < target_ratio * 0.8:
        return "дефіцит N", ratio
    elif ratio > target_ratio * 1.2:
        return "дефіцит P", ratio
    return "баланс", ratio

def get_optimal_k_range(gh):
    return {
        'min': gh * 1.2,
        'opt_low': gh * 1.5,
        'opt_high': gh * 2.5,
        'max': gh * 3.0,
        'target': gh * 1.8
    }

def calculate_steady_state(daily_dose, weekly_change_pct):
    if weekly_change_pct <= 0:
        return daily_dose * 365
    return (daily_dose * 7) / weekly_change_pct

def calculate_npk_ratio(n, p, k):
    total = n + p + k
    if total == 0:
        return (0, 0, 0)
    return (n/total, p/total, k/total)

def algae_risk(no3, po4):
    if po4 <= 0:
        return "Немає даних", 0
    ratio = no3 / po4
    if ratio < 8:
        return "🔴 Високий (дефіцит азоту → ціанобактерії)", ratio
    elif ratio > 25:
        return "🟠 Високий (дефіцит фосфору → зелені водорості)", ratio
    elif no3 > 30 or po4 > 1.5:
        return "🟡 Середній (надлишок макроелементів)", ratio
    elif no3 < 3 or po4 < 0.2:
        return "🟡 Середній (дефіцит живлення рослин)", ratio
    return "🟢 Низький", ratio

def light_recommendation(co2, no3, po4):
    if co2 < 20 or no3 < 5 or po4 < 0.2:
        return "💡 Низьке (50-70% потужності, 6-8 годин)"
    elif co2 > 30 and no3 > 10 and po4 > 0.5:
        return "⚡ Високе (90-100% потужності, 10-12 годин)"
    return "🌿 Середнє (70-90% потужності, 8-10 годин)"

def check_shock(prev_val, new_val, param_name, threshold=30):
    if prev_val and prev_val > 0:
        change_pct = abs((new_val - prev_val) / prev_val * 100)
        if change_pct > threshold:
            alert = f"⚠️ Різка зміна {param_name}: {change_pct:.0f}% за один період"
            if alert not in st.session_state.alerts:
                st.session_state.alerts.append(alert)
            return True
    return False

def save_snapshot(params, note=""):
    record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'note': note,
        **params
    }
    st.session_state.history.append(record)
    if len(st.session_state.history) > 100:
        st.session_state.history = st.session_state.history[-100:]

def calc_real_cons(tab, name, key_p, tank_vol, is_po4=False):
    with tab:
        c1, c2, c3 = st.columns(3)
        if is_po4:
            p_test = c1.number_input(f"Тест {name} (початок)", value=1.0, step=0.05, format="%.2f", key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=0.5, step=0.05, format="%.2f", key=f"c_{key_p}")
        else:
            p_test = c1.number_input(f"Тест {name} (початок)", value=15.0, step=0.5, format="%.1f", key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=10.0, step=0.5, format="%.1f", key=f"c_{key_p}")
        with c3:
            st.markdown("**Внесено добрив:**")
            dose_ml = st.number_input("мл добрива", value=0.0, step=1.0, format="%.1f", key=f"d_ml_{key_p}")
            if is_po4:
                conc = st.number_input(f"Концентрація {name} г/л", value=5.0, step=0.5, format="%.1f", key=f"conc_{key_p}")
            else:
                conc = st.number_input(f"Концентрація {name} г/л", value=50.0, step=5.0, format="%.1f", key=f"conc_{key_p}")
            added_mgl = (dose_ml * conc) / tank_vol if tank_vol > 0 else 0
            st.caption(f"Додано: +{added_mgl:.2f} мг/л")
        cl1, cl2 = st.columns(2)
        ch_l = cl1.number_input("Літрів підмінено", value=0.0, step=5.0, format="%.1f", key=f"ch_l_{key_p}")
        days_between = cl2.number_input("Днів між тестами", value=7, min_value=1, step=1, key=f"d_{key_p}")
        pct_wc = (ch_l / tank_vol) if tank_vol > 0 else 0
        res = (p_test * (1 - pct_wc) + added_mgl - c_test) / days_between if days_between > 0 else 0
        val = max(res, 0)
        st.info(f"**Споживання {name}:** {val:.2f} мг/л в день")
        return val

# НОВ: автоматичний розрахунок споживання з історії
def auto_consumption_from_history(history, param, tank_vol):
    """Розраховує середнє споживання між сусідніми записами в історії."""
    if len(history) < 2:
        return None
    df = pd.DataFrame(history)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    consumptions = []
    for i in range(1, len(df)):
        dt_days = (df['timestamp'][i] - df['timestamp'][i-1]).total_seconds() / 86400
        if dt_days < 0.1:
            continue
        delta = df[param][i-1] - df[param][i]
        cons_per_day = delta / dt_days
        if cons_per_day > 0:
            consumptions.append(cons_per_day)
    if consumptions:
        return round(float(np.median(consumptions)), 3)
    return None

# НОВ: детектор дрейфу
def detect_drift(history, param, window=5):
    """Повертає тренд: +1 росте, -1 падає, 0 стабільно."""
    if len(history) < window:
        return 0, []
    df = pd.DataFrame(history).tail(window)
    vals = df[param].values.astype(float)
    if len(vals) < 2:
        return 0, vals.tolist()
    slope = np.polyfit(range(len(vals)), vals, 1)[0]
    std = np.std(vals)
    if std < 0.01:
        return 0, vals.tolist()
    if slope > std * 0.3:
        return 1, vals.tolist()
    elif slope < -std * 0.3:
        return -1, vals.tolist()
    return 0, vals.tolist()

# ======================== SIDEBAR ========================
with st.sidebar:
    st.header("⚙️ Конфігурація системи")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)

    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    target_tds = st.number_input("Ціль TDS", value=120.0, step=5.0)

    st.divider()
    st.subheader("🔬 Розширені налаштування")
    custom_redfield = st.slider("Бажана пропорція Редфілда (N:P)", 5, 30, 15)

    po4_unit = st.radio("Тест показує:", ["PO4 (фосфат)", "P (фосфор)"], horizontal=True)
    if po4_unit == "P (фосфор)":
        target_po4_real = target_po4 * 3.07
        st.caption("⚠️ Ваші цілі будуть автоматично перераховані: P × 3.07 = PO4")
    else:
        target_po4_real = target_po4

    co2_min_opt = st.slider("Нижня межа CO₂ (мг/л)", 0, 100, 25)
    co2_max_opt = st.slider("Верхня межа CO₂ (мг/л)", 0, 100, 45)
    days = st.slider("Період прогнозу (днів)", 1, 30, 7)

# Алерти вгорі сторінки
if st.session_state.alerts:
    for alert in st.session_state.alerts:
        st.warning(alert)
    if st.button("✖ Закрити сповіщення"):
        st.session_state.alerts = []
        st.rerun()

# ======================== 1. РЕМІНЕРАЛІЗАТОР ========================
st.header("💎 1. Ремінералізатор")
with st.expander("Розрахунок солей для підміни", expanded=True):
    col_rem1, col_rem2 = st.columns(2)
    with col_rem1:
        c_vol = st.number_input("Літрів свіжої води (осмос)", value=10.0, step=5.0, key="rem_vol")
        st.divider()
        st.subheader("🎯 Цільові параметри")
        target_gh = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5)
        target_kh = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5)
        target_ca_mg_ratio = st.slider("Цільове Ca:Mg", 1.0, 6.0, 3.0, 0.5)
    with col_rem2:
        st.subheader("🧪 Розрахований склад")
        denom = (target_ca_mg_ratio / 5.1) + (1.0 / 4.3)
        mg_mgl = target_gh / denom if denom > 0 else 0
        ca_mgl = target_ca_mg_ratio * mg_mgl
        total_ca_g = ca_mgl * c_vol / 1000
        total_mg_g = mg_mgl * c_vol / 1000
        kh_from_caco3 = (target_kh * 17.86 * c_vol / 1000)
        ca_from_caco3_g = kh_from_caco3 * 0.4
        remaining_ca_g = max(0, total_ca_g - ca_from_caco3_g)
        cacl2_g = remaining_ca_g / 0.273 if remaining_ca_g > 0 else 0
        mgso4_g = total_mg_g / 0.0986 if total_mg_g > 0 else 0
        st.success(f"""
        **Для {c_vol:.0f} л осмосу додай:**
        🧂 **{kh_from_caco3:.3f} г** CaCO₃ | 🧂 **{cacl2_g:.3f} г** CaCl₂·2H₂O | 🧂 **{mgso4_g:.3f} г** MgSO₄·7H₂O
        """)
        st.caption(f"Ca у воді: {ca_mgl:.1f} мг/л | Mg у воді: {mg_mgl:.1f} мг/л | TDS ~{target_gh*10+target_kh*5:.0f} ppm")
        if cacl2_g < 0.01:
            st.info("💡 CaCO₃ дає достатньо кальцію, CaCl₂ не потрібен.")
        elif cacl2_g > 1.0:
            st.warning("⚠️ Потрібно багато CaCl₂ — перевірте параметри.")

# ======================== 2. КАЛЬКУЛЯТОР СПОЖИВАННЯ ========================
st.header("📊 2. Калькулятор реального споживання")
consumption_results = {}
with st.expander("Аналіз минулого періоду"):
    t1, t2, t3 = st.tabs(["NO3", "PO4", "K"])
    consumption_results['NO3'] = calc_real_cons(t1, "NO3", "no3", tank_vol)
    consumption_results['PO4'] = calc_real_cons(t2, "PO4", "po4", tank_vol, is_po4=True)
    consumption_results['K'] = calc_real_cons(t3, "K", "k", tank_vol)

# ======================== 3. ПОТОЧНИЙ СТАН ========================
st.header("📋 3. Поточні параметри води")
col1, col2, col3 = st.columns(3)
with col1:
    no3_now = st.number_input("NO3 (мг/л)", value=10.0, step=0.5, format="%.1f")
    if po4_unit == "P (фосфор)":
        po4_input = st.number_input("P (мг/л)", value=0.3, step=0.05, format="%.2f")
        po4_now = po4_input * 3.07
        st.caption(f"PO4 = {po4_now:.2f} мг/л")
    else:
        po4_now = st.number_input("PO4 (мг/л)", value=0.5, step=0.05, format="%.2f")
    k_now = st.number_input("K (мг/л)", value=10.0, step=0.5, format="%.1f")
    base_tds = st.number_input("TDS", value=150.0, step=5.0, format="%.0f")
with col2:
    gh = st.number_input("GH (°dH)", value=6, step=1)
    kh = st.number_input("KH (°dH)", value=2, step=1)
    st.divider()
    st.caption("🌬️ CO₂ контроль")
    ph_morning = st.number_input("pH (ранок, до CO₂)", value=7.2, step=0.1, format="%.1f")
    ph_evening = st.number_input("pH (вечір, через 2-3 год CO₂)", value=6.8, step=0.1, format="%.1f")
    co2_val = calculate_co2(kh, ph_evening)
    st.metric("Розрахунковий CO₂", f"{co2_val:.1f} мг/л")
with col3:
    # Якщо є достатньо історії — підставляємо авто-споживання
    auto_no3 = auto_consumption_from_history(st.session_state.history, 'no3', tank_vol)
    auto_po4 = auto_consumption_from_history(st.session_state.history, 'po4', tank_vol)
    auto_k   = auto_consumption_from_history(st.session_state.history, 'k', tank_vol)

    def_no3 = auto_no3 if auto_no3 else consumption_results.get('NO3', 2.0)
    def_po4 = auto_po4 if auto_po4 else consumption_results.get('PO4', 0.1)
    def_k   = auto_k   if auto_k   else consumption_results.get('K', 1.0)

    if auto_no3:
        st.caption("🤖 Споживання розраховано автоматично з історії")
    daily_no3 = st.number_input("Споживання NO3 (мг/л/день)", value=float(def_no3), step=0.1, format="%.1f")
    daily_po4 = st.number_input("Споживання PO4 (мг/л/день)", value=float(def_po4), step=0.05, format="%.2f")
    daily_k   = st.number_input("Споживання K (мг/л/день)",   value=float(def_k),   step=0.1, format="%.1f")

if st.session_state.last_params:
    lp = st.session_state.last_params
    check_shock(lp.get('no3'), no3_now, "NO₃")
    check_shock(lp.get('po4'), po4_now, "PO₄")
    check_shock(lp.get('k'),   k_now,   "K")

# ======================== 4. ПІДМІНА ВОДИ ========================
st.divider()
st.header("💧 4. Підміна води")
c_change, c_dosing = st.columns(2)
with c_change:
    change_l = st.number_input("Літри підміни", value=50.0, step=1.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.metric("Відсоток підміни", f"{pct*100:.1f}%")
    weekly_change_pct = pct * 7 if pct > 0 else 0
    steady_no3 = calculate_steady_state(daily_no3, weekly_change_pct)
    st.caption(f"⚖️ Steady State NO₃: {steady_no3:.0f} мг/л")
with c_dosing:
    st.markdown("**➕ Внесення добрив ПІСЛЯ підміни:**")
    col_n, col_p, col_k = st.columns(3)
    with col_n:
        dose_after_n_ml = st.number_input("N мл", value=0.0, step=1.0, key="after_n")
        conc_n = st.number_input("N г/л", value=50.0, key="conc_n_after")
        add_n_after = (dose_after_n_ml * conc_n) / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_n_after:.1f} мг/л NO3")
    with col_p:
        dose_after_p_ml = st.number_input("P мл", value=0.0, step=0.5, key="after_p")
        conc_p = st.number_input("P г/л", value=5.0, key="conc_p_after")
        add_p_after = (dose_after_p_ml * conc_p) / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_p_after:.2f} мг/л PO4")
    with col_k:
        dose_after_k_ml = st.number_input("K мл", value=0.0, step=1.0, key="after_k")
        conc_k = st.number_input("K г/л", value=20.0, key="conc_k_after")
        add_k_after = (dose_after_k_ml * conc_k) / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_k_after:.1f} мг/л K")

after_no3 = no3_now * (1 - pct) + add_n_after
after_po4 = po4_now * (1 - pct) + add_p_after
after_k   = k_now   * (1 - pct) + add_k_after
after_tds = base_tds * (1 - pct) + (add_n_after + add_p_after + add_k_after) * 0.5
st.info(f"**📈 Після підміни та внесення:** NO₃ = {after_no3:.1f} | PO₄ = {after_po4:.2f} | K = {after_k:.1f} | TDS = {after_tds:.0f}")

# ======================== 5. ДОЗУВАННЯ ДОБРИВ ========================
st.header("🧪 5. Дозування добрив")
cd_n, cd_p, cd_k = st.columns(3)
with cd_n:
    conc_n_daily = st.number_input("N (NO3) г/л", value=50.0, step=5.0, key="conc_n_daily")
    current_dose_n_ml = st.number_input("Поточна доза N мл/день", value=0.0, step=1.0, key="dose_n_daily")
    add_no3_daily = (current_dose_n_ml * conc_n_daily) / tank_vol if tank_vol > 0 else 0
with cd_p:
    conc_p_daily = st.number_input("P (PO4) г/л", value=5.0, step=0.5, key="conc_p_daily")
    current_dose_p_ml = st.number_input("Поточна доза P мл/день", value=0.0, step=0.5, key="dose_p_daily")
    add_po4_daily = (current_dose_p_ml * conc_p_daily) / tank_vol if tank_vol > 0 else 0
with cd_k:
    conc_k_daily = st.number_input("K г/л", value=20.0, step=2.0, key="conc_k_daily")
    current_dose_k_ml = st.number_input("Поточна доза K мл/день", value=0.0, step=1.0, key="dose_k_daily")
    add_k_daily = (current_dose_k_ml * conc_k_daily) / tank_vol if tank_vol > 0 else 0

final_no3 = after_no3 + add_no3_daily
final_po4 = after_po4 + add_po4_daily
final_k   = after_k   + add_k_daily
final_tds = after_tds + (add_no3_daily + add_po4_daily + add_k_daily) * 0.5

# ======================== 6. ПРОГНОЗ + СИМУЛЯТОР ========================
st.header(f"📈 6. Динамічний прогноз + Симулятор «Що якщо»")

# --- Симулятор сценаріїв (НОВА ФУНКЦІЯ) ---
with st.expander("🔬 Симулятор сценаріїв «Що якщо»", expanded=True):
    st.caption("Змінюйте параметри нижче — прогноз оновлюється миттєво, не впливаючи на основні налаштування")
    sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)
    with sim_col1:
        sim_dose_n = st.slider("N доза (мл/день)", 0.0, 30.0, float(current_dose_n_ml), 0.5, key="sim_n")
    with sim_col2:
        sim_dose_p = st.slider("P доза (мл/день)", 0.0, 20.0, float(current_dose_p_ml), 0.1, key="sim_p")
    with sim_col3:
        sim_dose_k = st.slider("K доза (мл/день)", 0.0, 30.0, float(current_dose_k_ml), 0.5, key="sim_k")
    with sim_col4:
        sim_wc_pct = st.slider("Підміна (%/тижд.)", 0, 80, int(weekly_change_pct * 100), 5, key="sim_wc")

    sim_add_n = (sim_dose_n * conc_n_daily) / tank_vol if tank_vol > 0 else 0
    sim_add_p = (sim_dose_p * conc_p_daily) / tank_vol if tank_vol > 0 else 0
    sim_add_k = (sim_dose_k * conc_k_daily) / tank_vol if tank_vol > 0 else 0
    sim_wc_daily = (sim_wc_pct / 100) / 7

    sim_forecast = []
    sn, sp, sk = final_no3, final_po4, final_k
    for d in range(days + 1):
        sim_forecast.append({"День": d, "NO3 (сим)": round(sn, 1), "PO4 (сим)": round(sp, 2), "K (сим)": round(sk, 1)})
        sn = clamp(sn * (1 - sim_wc_daily) + sim_add_n - daily_no3, 0, 200)
        sp = clamp(sp * (1 - sim_wc_daily) + sim_add_p - daily_po4, 0, 20)
        sk = clamp(sk * (1 - sim_wc_daily) + sim_add_k - daily_k,   0, 200)

    df_sim = pd.DataFrame(sim_forecast).set_index("День")

    # Порівняльний прогноз: поточний vs симульований
    forecast_base = []
    curr_n, curr_p, curr_k = final_no3, final_po4, final_k
    for d in range(days + 1):
        forecast_base.append({"День": d, "NO3": round(curr_n, 1), "PO4": round(curr_p, 2), "K": round(curr_k, 1)})
        dn = (current_dose_n_ml * conc_n_daily / tank_vol) if tank_vol > 0 else 0
        dp = (current_dose_p_ml * conc_p_daily / tank_vol) if tank_vol > 0 else 0
        dk = (current_dose_k_ml * conc_k_daily / tank_vol) if tank_vol > 0 else 0
        curr_n = clamp(curr_n + dn - daily_no3, 0, 200)
        curr_p = clamp(curr_p + dp - daily_po4, 0, 20)
        curr_k = clamp(curr_k + dk - daily_k,   0, 200)

    df_base = pd.DataFrame(forecast_base).set_index("День")

    # Об'єднаний графік порівняння
    df_compare = df_base[["NO3"]].rename(columns={"NO3": "NO3 (поточне)"})
    df_compare["NO3 (симуляція)"] = df_sim["NO3 (сим)"]
    st.line_chart(df_compare)

    sim_end = sim_forecast[-1]
    base_end = forecast_base[-1]
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("NO3 через {days}д (сим)".format(days=days), f"{sim_end['NO3 (сим)']:.1f} мг/л",
               delta=f"{sim_end['NO3 (сим)'] - base_end['NO3']:.1f} vs поточне")
    sc2.metric("PO4 через {days}д (сим)".format(days=days), f"{sim_end['PO4 (сим)']:.2f} мг/л",
               delta=f"{sim_end['PO4 (сим)'] - base_end['PO4']:.2f} vs поточне")
    sc3.metric("K через {days}д (сим)".format(days=days),   f"{sim_end['K (сим)']:.1f} мг/л",
               delta=f"{sim_end['K (сим)'] - base_end['K']:.1f} vs поточне")

# --- Основний прогноз ---
st.subheader("📊 Поточний прогноз")
df_forecast = df_base.copy()
f_end = forecast_base[-1]
st.line_chart(df_forecast)

# ======================== 7. WATERFALL — БАЛАНС ЗА ТИЖДЕНЬ ========================
st.header("🌊 7. Waterfall — баланс елементів за тиждень")

with st.expander("Візуалізація потоків NO3 / PO4 / K", expanded=True):
    wf_param = st.selectbox("Елемент:", ["NO3", "PO4", "K"], key="wf_param")

    if wf_param == "NO3":
        wf_start = no3_now
        wf_cons  = daily_no3 * 7
        wf_dose  = add_no3_daily * 7 + add_n_after
        wf_wc    = no3_now * pct * (7 if weekly_change_pct > 0 else 1)
        wf_unit  = "мг/л"
    elif wf_param == "PO4":
        wf_start = po4_now
        wf_cons  = daily_po4 * 7
        wf_dose  = add_po4_daily * 7 + add_p_after
        wf_wc    = po4_now * pct * (7 if weekly_change_pct > 0 else 1)
        wf_unit  = "мг/л"
    else:
        wf_start = k_now
        wf_cons  = daily_k * 7
        wf_dose  = add_k_daily * 7 + add_k_after
        wf_wc    = k_now * pct * (7 if weekly_change_pct > 0 else 1)
        wf_unit  = "мг/л"

    wf_end = wf_start - wf_cons - wf_wc + wf_dose

    wf_data = {
        "Категорія": ["Початок тижня", "− Споживання рослинами", "− Підміна води", "+ Внесення добрив", "Кінець тижня"],
        "мг/л": [wf_start, -wf_cons, -wf_wc, wf_dose, wf_end],
        "Тип": ["start", "negative", "negative", "positive", "end"]
    }
    df_wf = pd.DataFrame(wf_data)

    # Кумулятивний waterfall
    running = [wf_start]
    for v in [-wf_cons, -wf_wc, wf_dose]:
        running.append(running[-1] + v)

    wf_chart_data = pd.DataFrame({
        "Крок": wf_data["Категорія"][:-1],
        "Значення": [wf_start, wf_cons, wf_wc, wf_dose],
        "База": [0, running[0] - wf_cons, running[1] - wf_wc, running[2]]
    }).set_index("Крок")

    col_wf1, col_wf2 = st.columns([2, 1])
    with col_wf1:
        st.bar_chart(wf_chart_data[["Значення"]])
    with col_wf2:
        st.markdown(f"**{wf_param} за тиждень:**")
        st.metric("Початок", f"{wf_start:.2f} {wf_unit}")
        st.metric("− Споживання", f"{wf_cons:.2f} {wf_unit}")
        st.metric("− Підміна", f"{wf_wc:.2f} {wf_unit}")
        st.metric("+ Внесення", f"{wf_dose:.2f} {wf_unit}")
        delta_color = "normal"
        st.metric("= Кінець тижня", f"{wf_end:.2f} {wf_unit}",
                  delta=f"{wf_end - wf_start:+.2f}",
                  delta_color=delta_color)

# ======================== 8. K/GH АНАЛІЗ ========================
st.header("🧂 8. K/GH співвідношення")
k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("📐 Аналіз K/GH", expanded=True):
    st.markdown(f"""
    **Для вашого GH = {gh} °dH:**
    Мінімум K: **{k_opt_range['min']:.1f}** | Оптимум: **{k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f}** | Максимум: **{k_opt_range['max']:.1f}** мг/л
    """)
    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        st.metric("Поточний K", f"{final_k:.1f} мг/л")
        st.caption(f"GH = {gh} °dH")
    with col_k2:
        st.metric("K/GH ratio", f"{k_gh_ratio:.2f}", delta="норма 1.5-2.5")
    with col_k3:
        if final_k < k_opt_range['min']:
            st.error(f"🔴 КРИТИЧНИЙ ДЕФІЦИТ K — +{k_opt_range['min'] - final_k:.1f} мг/л")
        elif final_k < k_opt_range['opt_low']:
            st.warning(f"🟡 Дефіцит K — підніміть до {k_opt_range['opt_low']:.0f} мг/л")
        elif final_k <= k_opt_range['opt_high']:
            st.success("✅ K в нормі")
        elif final_k <= k_opt_range['max']:
            st.warning(f"🟡 Надлишок K — знизьте на {final_k - k_opt_range['opt_high']:.1f} мг/л")
        else:
            st.error("🔴 КРИТИЧНИЙ НАДЛИШОК K — терміново знизьте")

# ======================== 9. ШІ АНАЛІЗ ========================
st.header("🤖 9. Штучний Інтелект — Аналіз та рекомендації")
algae, np_ratio = algae_risk(final_no3, final_po4)
light = light_recommendation(co2_val, final_no3, final_po4)
npk_ratio = calculate_npk_ratio(final_no3, final_po4, final_k)

st.info(f"**🌊 Ризик водоростей:** {algae}")
st.info(f"**💡 Рекомендація по світлу:** {light}")
st.caption(f"**📊 NPK:** {npk_ratio[0]:.2f} : {npk_ratio[1]:.2f} : {npk_ratio[2]:.2f}")

st.subheader("💡 Поточні рекомендації")
recommendations = []
if final_no3 < 5:
    recommendations.append("🔴 Дуже низький NO3 (<5 мг/л) — терміново збільште N")
elif final_no3 < 10:
    recommendations.append("🟡 Низький NO3 — збільште N на 20%")
elif final_no3 > 40:
    recommendations.append("🔴 Високий NO3 (>40 мг/л) — зменште N")
elif final_no3 > 30:
    recommendations.append("🟡 Підвищений NO3 — зменште N на 20%")
if final_po4 < 0.2:
    recommendations.append("🔴 Дуже низький PO4 — збільште P")
elif final_po4 < 0.5:
    recommendations.append("🟡 Низький PO4 — фосфор може бути лімітуючим")
elif final_po4 > 2.5:
    recommendations.append("🔴 Високий PO4 — ризик водоростей")
elif final_po4 > 1.5:
    recommendations.append("🟡 Підвищений PO4 — слідкуйте за водоростями")
if final_k < k_opt_range['opt_low']:
    recommendations.append(f"🔴 Дефіцит K ({final_k:.1f} < {k_opt_range['opt_low']:.0f} мг/л)")
elif final_k > k_opt_range['opt_high']:
    recommendations.append("🟡 Надлишок K — можливе блокування Ca/Mg")
if co2_val < co2_min_opt:
    recommendations.append(f"🔴 Дефіцит CO₂ ({co2_val:.1f} < {co2_min_opt} мг/л)")
elif co2_val > co2_max_opt:
    recommendations.append(f"🔴 Надлишок CO₂ ({co2_val:.1f} > {co2_max_opt} мг/л) — ризик для риб")
if recommendations:
    for rec in recommendations[:5]:
        st.warning(rec)
else:
    st.success("✅ Всі параметри в оптимальному діапазоні!")

# ======================== 10. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.header("📅 10. План корекції дозування")

delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4_real - f_end["PO4"]
delta_k   = target_k - f_end["K"]

def calc_dose_correction(delta, days, conc, current_ml, tank_vol):
    if abs(delta) < 0.01:
        return current_ml, "без змін"
    daily_delta = abs(delta) / days if days > 0 else 0
    change_ml = (daily_delta * tank_vol) / conc if conc > 0 else 0
    if delta > 0:
        return current_ml + change_ml, f"+{change_ml:.2f} мл/день"
    else:
        return max(0, current_ml - change_ml), f"-{change_ml:.2f} мл/день"

new_dose_n, action_n = calc_dose_correction(delta_no3, days, conc_n_daily, current_dose_n_ml, tank_vol)
new_dose_p, action_p = calc_dose_correction(delta_po4, days, conc_p_daily, current_dose_p_ml, tank_vol)
new_dose_k, action_k = calc_dose_correction(delta_k,   days, conc_k_daily, current_dose_k_ml, tank_vol)

col_rec1, col_rec2, col_rec3 = st.columns(3)
with col_rec1:
    st.metric("N доза", f"{current_dose_n_ml:.1f} → {new_dose_n:.1f} мл/день", delta=action_n)
with col_rec2:
    st.metric("P доза", f"{current_dose_p_ml:.2f} → {new_dose_p:.2f} мл/день", delta=action_p)
with col_rec3:
    st.metric("K доза", f"{current_dose_k_ml:.1f} → {new_dose_k:.1f} мл/день", delta=action_k)
st.caption("💡 Змінюйте дозування поступово, не більше ніж на 20% за день")

# ======================== 11. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("📝 11. Експертний висновок")
redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)
with col_summary1:
    st.subheader("📊 Стан системи")
    if co2_val < co2_min_opt:
        st.warning(f"🌬️ CO₂: {co2_val:.1f} — дефіцит (норма {co2_min_opt}-{co2_max_opt})")
    elif co2_val > co2_max_opt:
        st.error(f"🌬️ CO₂: {co2_val:.1f} — надлишок")
    else:
        st.success(f"✅ CO₂: {co2_val:.1f} мг/л — норма")
    if redfield_status == "дефіцит N":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — дефіцит азоту")
    elif redfield_status == "дефіцит P":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — дефіцит фосфору")
    else:
        st.success(f"✅ N:P = {redfield_ratio:.1f}:1 — баланс")
    if final_k < k_opt_range['opt_low']:
        st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — дефіцит K")
    elif final_k > k_opt_range['opt_high']:
        st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — надлишок K")
    else:
        st.success(f"✅ K/GH = {k_gh_ratio:.2f} — норма")

with col_summary2:
    st.subheader(f"📈 Прогноз через {days} днів")
    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л", delta=f"{f_end['NO3'] - final_no3:.1f}")
    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л", delta=f"{f_end['PO4'] - final_po4:.2f}")
    st.metric("K",   f"{f_end['K']:.1f} мг/л",   delta=f"{f_end['K'] - final_k:.1f}")
    if f_end['NO3'] < 3:
        st.error("⚠️ Прогнозується критичне падіння NO₃!")
    if f_end['PO4'] < 0.1:
        st.error("⚠️ Прогнозується критичне падіння PO₄!")
    if f_end['K'] < k_opt_range['min']:
        st.error(f"⚠️ Прогнозується падіння K нижче {k_opt_range['min']:.0f} мг/л!")

# ======================== 12. ЗВІТ ========================
st.divider()
st.subheader("📋 12. Звіт для журналу")
report = f"""=== TOXICODE AQUARIUM V11 REPORT ===
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л | pH: {ph_morning}→{ph_evening}

МАКРОЕЛЕМЕНТИ
NO3: {final_no3:.1f} → {target_no3} мг/л
PO4: {final_po4:.2f} → {target_po4_real:.2f} мг/л
K:   {final_k:.1f} → {target_k} мг/л

БАЛАНСИ
N:P = {redfield_ratio:.1f}:1 ({redfield_status}) | K/GH = {k_gh_ratio:.2f}

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ
NO3: {f_end['NO3']:.1f} | PO4: {f_end['PO4']:.2f} | K: {f_end['K']:.1f} мг/л

ШІ: {algae} | {light}

КОРЕКЦІЯ ДОЗИ
N: {current_dose_n_ml:.1f}→{new_dose_n:.1f} | P: {current_dose_p_ml:.2f}→{new_dose_p:.2f} | K: {current_dose_k_ml:.1f}→{new_dose_k:.1f} мл/день
====================================="""
st.code(report, language="text")

# ======================== 13. ІСТОРІЯ + АНАЛІТИКА ========================
with st.expander("📜 13. Історія та аналітика", expanded=False):
    col_save1, col_save2 = st.columns([3, 1])
    with col_save1:
        save_note = st.text_input("Нотатка", key="save_note", placeholder="Наприклад: після підміни...")
    with col_save2:
        if st.button("💾 Зберегти", key="manual_save"):
            current_params = {
                'no3': final_no3, 'po4': final_po4, 'k': final_k,
                'tds': final_tds, 'gh': gh, 'kh': kh, 'co2': co2_val
            }
            save_snapshot(current_params, note=save_note)
            st.session_state.last_params = current_params
            st.success(f"✅ Збережено ({datetime.now().strftime('%H:%M:%S')})")
            st.rerun()

    st.divider()

    if st.session_state.history:
        df_history = pd.DataFrame(st.session_state.history)
        df_history['timestamp'] = pd.to_datetime(df_history['timestamp'])
        df_history_sorted = df_history.sort_values('timestamp')

        # --- Таблиця ---
        df_history['дата'] = df_history['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        disp_cols = ['дата', 'note', 'no3', 'po4', 'k', 'tds', 'gh', 'kh', 'co2']
        disp_names = ['Дата', 'Нотатка', 'NO3', 'PO4', 'K', 'TDS', 'GH', 'KH', 'CO₂']
        st.dataframe(df_history[disp_cols].tail(10).rename(columns=dict(zip(disp_cols, disp_names))),
                     use_container_width=True)

        if len(df_history) > 1:
            # --- Мультилінійний графік всіх елементів ---
            st.subheader("📈 Динаміка всіх елементів")
            chart_param = st.multiselect("Показати:", ["no3", "po4", "k", "co2"],
                                          default=["no3", "po4", "k"], key="hist_params")
            if chart_param:
                df_chart = df_history_sorted.set_index('timestamp')[chart_param]
                st.line_chart(df_chart)

            # --- N:P ratio в часі (НОВА ФУНКЦІЯ) ---
            st.subheader("⚖️ N:P ratio в часі")
            df_np = df_history_sorted.copy()
            df_np['NP_ratio'] = df_np.apply(
                lambda r: r['no3'] / r['po4'] if r['po4'] > 0 else None, axis=1)
            df_np_chart = df_np.set_index('timestamp')[['NP_ratio']].dropna()
            if len(df_np_chart) > 1:
                st.line_chart(df_np_chart)
                st.caption(f"Цільовий N:P = {custom_redfield}:1 | Норма: {custom_redfield*0.8:.0f}–{custom_redfield*1.2:.0f}")

            # --- Детектор дрейфу (НОВА ФУНКЦІЯ) ---
            st.subheader("🔍 Детектор дрейфу")
            drift_cols = st.columns(3)
            for i, (param, label, unit) in enumerate([('no3','NO3','мг/л'), ('po4','PO4','мг/л'), ('k','K','мг/л')]):
                trend, vals = detect_drift(st.session_state.history, param)
                with drift_cols[i]:
                    if trend == 1:
                        st.warning(f"📈 {label} стабільно **росте**")
                        st.caption("Перевірте: чи не перевищено дозу?")
                    elif trend == -1:
                        st.warning(f"📉 {label} стабільно **падає**")
                        st.caption("Перевірте: споживання зросло або доза мала?")
                    else:
                        st.success(f"✅ {label} стабільний")

            # --- Авто-споживання з кореляцій (НОВА ФУНКЦІЯ) ---
            st.subheader("🤖 Авторозрахунок споживання з історії")
            auto_cols = st.columns(3)
            for i, (param, label) in enumerate([('no3','NO3'), ('po4','PO4'), ('k','K')]):
                val = auto_consumption_from_history(st.session_state.history, param, tank_vol)
                with auto_cols[i]:
                    if val:
                        st.metric(f"{label} споживання", f"{val:.3f} мг/л/день",
                                  help="Медіана між усіма сусідніми парами записів")
                    else:
                        st.caption(f"{label}: потрібно ≥2 записи")

        if st.button("🗑️ Очистити історію", key="clear_history"):
            st.session_state.history = []
            st.session_state.alerts = []
            st.rerun()
    else:
        st.info("Поки немає збережених даних. Зберігайте показники 1 раз на день для аналітики.")
        st.caption("💡 Після 2+ записів з'являться: автоматичний розрахунок споживання, детектор дрейфу, графік N:P ratio.")

# ======================== 14. ТЕПЛОВА КАРТА (НОВА ФУНКЦІЯ) ========================
with st.expander("🌡️ 14. Теплова карта параметрів по днях прогнозу"):
    heatmap_data = {}
    params_forecast = [
        ("NO3", 5, 30, [r["NO3"] for r in forecast_base]),
        ("PO4", 0.2, 1.5, [r["PO4"] for r in forecast_base]),
        ("K",   k_opt_range['opt_low'], k_opt_range['opt_high'], [r["K"] for r in forecast_base]),
    ]
    for name, lo, hi, vals in params_forecast:
        status_row = []
        for v in vals:
            if v < lo * 0.7:
                status_row.append(-2)   # критичний дефіцит
            elif v < lo:
                status_row.append(-1)   # дефіцит
            elif v <= hi:
                status_row.append(0)    # норма
            elif v <= hi * 1.3:
                status_row.append(1)    # підвищений
            else:
                status_row.append(2)    # критичний надлишок
        heatmap_data[name] = status_row

    df_heatmap = pd.DataFrame(heatmap_data, index=[f"День {d}" for d in range(days + 1)])

    st.caption("Значення: -2 критичний дефіцит | -1 дефіцит | 0 норма | +1 підвищений | +2 надлишок")
    st.dataframe(
        df_heatmap.style.background_gradient(cmap='RdYlGn', vmin=-2, vmax=2),
        use_container_width=True
    )

# ======================== 15. ВАЛІДАЦІЯ ========================
with st.expander("🛡️ 15. Валідація та безпека"):
    st.markdown(f"""
    | Перевірка | Поточне | Безпечний діапазон | Статус |
    |-----------|---------|--------------------|--------|
    | NO3 | {final_no3:.1f} | 5-40 | {"✅" if 5 <= final_no3 <= 40 else "⚠️"} |
    | PO4 | {final_po4:.2f} | 0.2-2.5 | {"✅" if 0.2 <= final_po4 <= 2.5 else "⚠️"} |
    | CO₂ | {co2_val:.1f} | {co2_min_opt}-{co2_max_opt} | {"✅" if co2_min_opt <= co2_val <= co2_max_opt else "⚠️"} |
    | K/GH | {k_gh_ratio:.2f} | 1.5-2.5 | {"✅" if 1.5 <= k_gh_ratio <= 2.5 else "⚠️"} |
    """)
    if final_no3 > 40:
        st.error("🚨 Високий NO3 — зменште N")
    if final_po4 > 2.5:
        st.warning("⚠️ Високий PO4 — ризик водоростей")
    if co2_val > co2_max_opt:
        st.error("🚨 Зменште подачу CO₂")
    if final_k > k_opt_range['max']:
        st.warning("⚠️ K вище максимуму — ризик блокування Ca/Mg")

st.caption("⚡ Toxicode V11 | Симулятор сценаріїв | Waterfall | Детектор дрейфу | Теплова карта | Авто-споживання")
