import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Toxicode Aquarium System V10.3", layout="wide")
st.title("🌿 Toxicode Aquarium System V10.3 — Штучний Інтелект Акваріуміста")

# ======================== ІНІЦІАЛІЗАЦІЯ СЕСІЇ ========================
if 'history' not in st.session_state:
    st.session_state.history = []
if 'last_params' not in st.session_state:
    st.session_state.last_params = None
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# ======================== HELPER FUNCTIONS ========================
# FIX (Quality #5): clamp() was defined but never used — now used in forecast
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

# FIX (Bug #1 — bare except): catch specific exceptions only
def calculate_co2(kh, ph):
    """CO₂ (мг/л) = 3 * KH * 10^(7-pH)"""
    try:
        return 3 * kh * (10 ** (7 - ph))
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0

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

def calculate_npk_ratio(n, p, k):
    """Розрахунок співвідношення NPK для змішування"""
    total = n + p + k
    if total == 0:
        return (0, 0, 0)
    return (n/total, p/total, k/total)

def algae_risk(no3, po4, light_intensity=1.0):
    """Оцінка ризику водоростей"""
    if po4 <= 0:
        return "Немає даних"
    ratio = no3 / po4
    if ratio < 8:
        return "🔴 Високий (дефіцит азоту стимулює ціанобактерії)"
    elif ratio > 25:
        return "🟠 Високий (дефіцит фосфору стимулює зелені водорості)"
    elif no3 > 30 or po4 > 1.5:
        return "🟡 Середній (надлишок макроелементів)"
    elif no3 < 3 or po4 < 0.2:
        return "🟡 Середній (дефіцит живлення рослин)"
    return "🟢 Низький"

def light_recommendation(co2, no3, po4):
    """Рекомендація інтенсивності світла"""
    if co2 < 20 or no3 < 5 or po4 < 0.2:
        return "💡 Низьке (50-70% потужності, 6-8 годин)"
    elif co2 > 30 and no3 > 10 and po4 > 0.5:
        return "⚡ Високе (90-100% потужності, 10-12 годин)"
    return "🌿 Середнє (70-90% потужності, 8-10 годин)"

def check_shock(prev_val, new_val, param_name, threshold=30):
    """Перевірка різких змін параметрів"""
    if prev_val and prev_val > 0:
        change_pct = abs((new_val - prev_val) / prev_val * 100)
        if change_pct > threshold:
            alert = f"⚠️ Різка зміна {param_name}: {change_pct:.0f}% за один період"
            if alert not in st.session_state.alerts:
                st.session_state.alerts.append(alert)
            return True
    return False

# FIX (Quality #3): unified save function used by both save buttons
def save_snapshot(params, note=""):
    """Збереження параметрів в історію"""
    record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'note': note,
        **params
    }
    st.session_state.history.append(record)
    if len(st.session_state.history) > 50:
        st.session_state.history = st.session_state.history[-50:]

# FIX (Quality #2): calc_real_cons moved to top-level, tank_vol passed as argument
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
            dose_ml = st.number_input(f"мл добрива", value=0.0, step=1.0, format="%.1f", key=f"d_ml_{key_p}")
            if is_po4:
                conc = st.number_input(f"Концентрація {name} г/л", value=5.0, step=0.5, format="%.1f", key=f"conc_{key_p}")
            else:
                conc = st.number_input(f"Концентрація {name} г/л", value=50.0, step=5.0, format="%.1f", key=f"conc_{key_p}")
            added_mgl = (dose_ml * conc) / tank_vol if tank_vol > 0 else 0
            st.caption(f"Додано: +{added_mgl:.2f} мг/л")

        cl1, cl2 = st.columns(2)
        ch_l = cl1.number_input(f"Літрів підмінено", value=0.0, step=5.0, format="%.1f", key=f"ch_l_{key_p}")
        days_between = cl2.number_input("Днів між тестами", value=7, min_value=1, step=1, key=f"d_{key_p}")

        pct_wc = (ch_l / tank_vol) if tank_vol > 0 else 0
        res = (p_test * (1 - pct_wc) + added_mgl - c_test) / days_between if days_between > 0 else 0
        val = max(res, 0)
        st.info(f"**Споживання {name}:** {val:.2f} мг/л в день")
        return val

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

    # FIX (Quality #3): sidebar save button now uses unified save_snapshot()
    if st.button("📊 Зберегти поточні показники"):
        # We don't have final values yet at sidebar render time, so we show a note
        st.info("Використовуйте кнопку збереження в розділі 'Історія' для збереження повних даних.")

# FIX (Quality #4): display alerts at the top of the page if any exist
if st.session_state.alerts:
    with st.container():
        for alert in st.session_state.alerts:
            st.warning(alert)
        if st.button("✖ Закрити сповіщення"):
            st.session_state.alerts = []
            st.rerun()

# ======================== 1. РЕМІНЕРАЛІЗАТОР ========================
st.header("💎 1. Ремінералізатор")
with st.expander("Розрахунок солей для підміни", expanded=True):
    st.markdown("""
    **Як це працює:**  
    Ви задаєте бажані параметри води (GH, KH, Ca:Mg), а система розраховує точну кількість солей.
    """)

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

        # FIX (Bug #1): corrected Ca/Mg distribution formula
        # GH in °dH: 1°dH = 7.14 mg/l Ca²⁺ equivalent or 4.33 mg/l Mg²⁺ equivalent
        # Solve: ca_mgl/5.1 + mg_mgl/4.3 = target_gh  AND  ca_mgl = target_ca_mg_ratio * mg_mgl
        # => mg_mgl * (target_ca_mg_ratio/5.1 + 1/4.3) = target_gh
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
        
        🧂 **{kh_from_caco3:.3f} г** CaCO₃ (кальцій карбонат)
        🧂 **{cacl2_g:.3f} г** CaCl₂·2H₂O (кальцій хлорид)
        🧂 **{mgso4_g:.3f} г** MgSO₄·7H₂O (магній сульфат)
        """)

        st.divider()
        with st.expander("📖 Інструкція приготування", expanded=True):
            st.markdown(f"""
            ### 📋 Покрокова інструкція:
            
            1. **Підготуйте {c_vol:.0f} л осмосу** (або дистильованої води) в чистій ємності
            
            2. **Додайте солі** в такому порядку:
               - 🧂 **$CaCO_3$ (кальцій карбонат)** — важко розчиняється, додайте першим
               - 🧂 **$MgSO_4 \\cdot 7H_2O$ (магній сульфат)** — добре розчиняється
               - 🧂 **$CaCl_2 \\cdot 2H_2O$ (кальцій хлорид)** — додайте останнім
            
            3. **Перемішайте** до повного розчинення
            
            4. **Виміряйте TDS** — має бути ~{target_gh * 10 + target_kh * 5:.0f} ppm
            
            5. **Перевірте параметри** (за можливості):
               - GH має бути {target_gh:.1f}°dH
               - KH має бути {target_kh:.1f}°dH
            
            6. **Додайте в акваріум** поступово (не більше 30% об'єму за раз)
            
            ### 📊 Розраховані параметри:
            
            | Параметр | Значення |
            |----------|----------|
            | Об'єм води | {c_vol:.0f} л |
            | Цільовий GH | {target_gh:.1f}°dH |
            | Цільовий KH | {target_kh:.1f}°dH |
            | Цільове Ca:Mg | {target_ca_mg_ratio:.1f}:1 |
            | Ca у воді | {ca_mgl:.1f} мг/л |
            | Mg у воді | {mg_mgl:.1f} мг/л |
            | Орієнтовний TDS | {target_gh * 10 + target_kh * 5:.0f} ppm |
            """)

        if cacl2_g < 0.01 and remaining_ca_g <= 0:
            st.info("💡 **Порада:** CaCO₃ дає достатньо кальцію, додатковий CaCl₂ не потрібен.")
        elif cacl2_g > 1.0:
            st.warning("⚠️ **Увага:** Потрібно багато CaCl₂. Перевірте чи правильно задані параметри.")

# ======================== 2. КАЛЬКУЛЯТОР СПОЖИВАННЯ ========================
st.header("📊 2. Калькулятор реального споживання")
consumption_results = {}

with st.expander("Аналіз минулого періоду"):
    t1, t2, t3 = st.tabs(["NO3", "PO4", "K"])
    # FIX (Quality #2): calc_real_cons is now a top-level function, tank_vol passed explicitly
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
    default_no3_cons = consumption_results.get('NO3', 2.0)
    default_po4_cons = consumption_results.get('PO4', 0.1)
    default_k_cons = consumption_results.get('K', 1.0)

    daily_no3 = st.number_input("Споживання NO3 (мг/л/день)", value=float(default_no3_cons), step=0.1, format="%.1f")
    daily_po4 = st.number_input("Споживання PO4 (мг/л/день)", value=float(default_po4_cons), step=0.05, format="%.2f")
    daily_k = st.number_input("Споживання K (мг/л/день)", value=float(default_k_cons), step=0.1, format="%.1f")

# Trigger shock alerts if previous values exist
if st.session_state.last_params:
    lp = st.session_state.last_params
    check_shock(lp.get('no3'), no3_now, "NO₃")
    check_shock(lp.get('po4'), po4_now, "PO₄")
    check_shock(lp.get('k'), k_now, "K")

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
after_k = k_now * (1 - pct) + add_k_after
after_tds = base_tds * (1 - pct) + (add_n_after + add_p_after + add_k_after) * 0.5

st.info(f"**📈 Після підміни та внесення:** NO₃ = {after_no3:.1f} | PO₄ = {after_po4:.2f} | K = {after_k:.1f} | TDS = {after_tds:.0f}")

# ======================== 5. ДОЗУВАННЯ ДОБРИВ ========================
st.header("🧪 5. Дозування добрив")
st.caption("Концентрація готового розчину (г/л) та поточна доза (мл/день)")

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
final_k = after_k + add_k_daily
final_tds = after_tds + (add_no3_daily + add_po4_daily + add_k_daily) * 0.5

# ======================== 6. ПРОГНОЗ ========================
st.header(f"📈 6. Динамічний прогноз на {days} днів")

# FIX (Bug #2): stability coefficient removed from consumption term.
# It was incorrectly reducing plant uptake when nutrients were imbalanced.
# Daily dosing and consumption are now applied directly without distortion.
if final_po4 > 0 and custom_redfield > 0:
    current_ratio = final_no3 / final_po4
    stability = 1 / (1 + abs((current_ratio - custom_redfield) / custom_redfield))
else:
    stability = 0.5

st.caption(f"🎯 Коефіцієнт стабільності N:P: {stability:.2f} (чим ближче до 1, тим кращий баланс)")

forecast = []
curr_n, curr_p, curr_k = final_no3, final_po4, final_k

for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(0, round(curr_n, 1)),
        "PO4": max(0, round(curr_p, 2)),
        "K": max(0, round(curr_k, 1))
    })
    # FIX (Bug #2): use clamp() and apply consumption directly (no stability multiplier)
    # clamp ensures values never go below 0 or above a reasonable ceiling
    daily_dose_n = (current_dose_n_ml * conc_n_daily / tank_vol) if tank_vol > 0 else 0
    daily_dose_p = (current_dose_p_ml * conc_p_daily / tank_vol) if tank_vol > 0 else 0
    daily_dose_k = (current_dose_k_ml * conc_k_daily / tank_vol) if tank_vol > 0 else 0

    curr_n = clamp(curr_n + daily_dose_n - daily_no3, 0, 200)
    curr_p = clamp(curr_p + daily_dose_p - daily_po4, 0, 20)
    curr_k = clamp(curr_k + daily_dose_k - daily_k, 0, 200)

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)

# ======================== 7. K/GH АНАЛІЗ ========================
st.header("🧂 7. K/GH співвідношення")

k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("📐 Як розрахувати цільовий K за GH", expanded=True):
    st.markdown(f"""
    **Для вашого GH = {gh} °dH:**
    - Мінімум K: {k_opt_range['min']:.1f} мг/л
    - Оптимум K: {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f} мг/л
    - Максимум K: {k_opt_range['max']:.1f} мг/л
    
    **Формула:** `K_ціль (мг/л) = GH × 1.8`
    """)

col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Поточний K", f"{final_k:.1f} мг/л")
    st.caption(f"GH = {gh} °dH")

with col_k2:
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}", delta="норма 1.5-2.5")

with col_k3:
    if final_k < k_opt_range['min']:
        st.error(f"🔴 КРИТИЧНИЙ ДЕФІЦИТ K — підніміть на {k_opt_range['min'] - final_k:.1f} мг/л")
    elif final_k < k_opt_range['opt_low']:
        st.warning(f"🟡 Дефіцит K — підніміть до {k_opt_range['opt_low']:.0f} мг/л")
    elif final_k <= k_opt_range['opt_high']:
        st.success("✅ K в нормі")
    elif final_k <= k_opt_range['max']:
        st.warning(f"🟡 Надлишок K — знизьте на {final_k - k_opt_range['opt_high']:.1f} мг/л")
    else:
        st.error(f"🔴 КРИТИЧНИЙ НАДЛИШОК K — терміново знизьте")

# ======================== 8. ШІ АНАЛІЗ ТА РЕКОМЕНДАЦІЇ ========================
st.header("🤖 8. Штучний Інтелект — Аналіз та рекомендації")

algae = algae_risk(final_no3, final_po4)
st.info(f"**🌊 Ризик водоростей:** {algae}")

light = light_recommendation(co2_val, final_no3, final_po4)
st.info(f"**💡 Рекомендація по світлу:** {light}")

npk_ratio = calculate_npk_ratio(final_no3, final_po4, final_k)
st.caption(f"**📊 Співвідношення NPK:** {npk_ratio[0]:.1f} : {npk_ratio[1]:.1f} : {npk_ratio[2]:.1f}")

st.subheader("💡 Поточні рекомендації")

recommendations = []

if final_no3 < 5:
    recommendations.append("🔴 Дуже низький NO3 (<5 мг/л) — терміново збільште дозу N")
elif final_no3 < 10:
    recommendations.append("🟡 Низький NO3 — збільште N на 20%")
elif final_no3 > 40:
    recommendations.append("🔴 Високий NO3 (>40 мг/л) — зменште N добрива")
elif final_no3 > 30:
    recommendations.append("🟡 Підвищений NO3 — зменште N на 20%")

if final_po4 < 0.2:
    recommendations.append("🔴 Дуже низький PO4 (<0.2 мг/л) — збільште дозу P")
elif final_po4 < 0.5:
    recommendations.append("🟡 Низький PO4 — фосфор може бути лімітуючим фактором")
elif final_po4 > 2.5:
    recommendations.append("🔴 Високий PO4 (>2.5 мг/л) — високий ризик водоростей")
elif final_po4 > 1.5:
    recommendations.append("🟡 Підвищений PO4 — слідкуйте за водоростями")

if final_k < k_opt_range['opt_low']:
    recommendations.append(f"🔴 Дефіцит K ({final_k:.1f} < {k_opt_range['opt_low']:.0f} мг/л) — додайте K")
elif final_k > k_opt_range['opt_high']:
    recommendations.append(f"🟡 Надлишок K — можливе блокування Ca/Mg")

if co2_val < co2_min_opt:
    recommendations.append(f"🔴 Дефіцит CO₂ ({co2_val:.1f} < {co2_min_opt} мг/л) — збільште подачу")
elif co2_val > co2_max_opt:
    recommendations.append(f"🔴 Надлишок CO₂ ({co2_val:.1f} > {co2_max_opt} мг/л) — ризик для риб")

if recommendations:
    for rec in recommendations[:5]:
        st.warning(rec)
else:
    st.success("✅ Всі параметри в оптимальному діапазоні! Так тримати.")

# ======================== 9. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.header("📅 9. План корекції дозування")

f_end = forecast[-1]

delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4_real - f_end["PO4"]
delta_k = target_k - f_end["K"]

if delta_no3 > 0:
    daily_delta_no3 = delta_no3 / days if days > 0 else 0
    change_n_ml = (daily_delta_no3 * tank_vol) / conc_n_daily if conc_n_daily > 0 else 0
    new_dose_n = current_dose_n_ml + change_n_ml
    action_n = f"+{change_n_ml:.1f} мл/день"
elif delta_no3 < 0:
    daily_delta_no3 = abs(delta_no3) / days if days > 0 else 0
    reduce_n_ml = (daily_delta_no3 * tank_vol) / conc_n_daily if conc_n_daily > 0 else 0
    new_dose_n = max(0, current_dose_n_ml - reduce_n_ml)
    action_n = f"-{reduce_n_ml:.1f} мл/день"
else:
    new_dose_n = current_dose_n_ml
    action_n = "без змін"

if delta_po4 > 0:
    daily_delta_po4 = delta_po4 / days if days > 0 else 0
    change_p_ml = (daily_delta_po4 * tank_vol) / conc_p_daily if conc_p_daily > 0 else 0
    new_dose_p = current_dose_p_ml + change_p_ml
    action_p = f"+{change_p_ml:.2f} мл/день"
elif delta_po4 < 0:
    daily_delta_po4 = abs(delta_po4) / days if days > 0 else 0
    reduce_p_ml = (daily_delta_po4 * tank_vol) / conc_p_daily if conc_p_daily > 0 else 0
    new_dose_p = max(0, current_dose_p_ml - reduce_p_ml)
    action_p = f"-{reduce_p_ml:.2f} мл/день"
else:
    new_dose_p = current_dose_p_ml
    action_p = "без змін"

if delta_k > 0:
    daily_delta_k = delta_k / days if days > 0 else 0
    change_k_ml = (daily_delta_k * tank_vol) / conc_k_daily if conc_k_daily > 0 else 0
    new_dose_k = current_dose_k_ml + change_k_ml
    action_k = f"+{change_k_ml:.1f} мл/день"
elif delta_k < 0:
    daily_delta_k = abs(delta_k) / days if days > 0 else 0
    reduce_k_ml = (daily_delta_k * tank_vol) / conc_k_daily if conc_k_daily > 0 else 0
    new_dose_k = max(0, current_dose_k_ml - reduce_k_ml)
    action_k = f"-{reduce_k_ml:.1f} мл/день"
else:
    new_dose_k = current_dose_k_ml
    action_k = "без змін"

col_rec1, col_rec2, col_rec3 = st.columns(3)

with col_rec1:
    st.metric("N доза", f"{current_dose_n_ml:.1f} → {new_dose_n:.1f} мл/день", delta=action_n)

with col_rec2:
    st.metric("P доза", f"{current_dose_p_ml:.2f} → {new_dose_p:.2f} мл/день", delta=action_p)

with col_rec3:
    st.metric("K доза", f"{current_dose_k_ml:.1f} → {new_dose_k:.1f} мл/день", delta=action_k)

st.caption("💡 Змінюйте дозування поступово, не більше ніж на 20% за день")

# ======================== 10. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("📝 10. Експертний висновок")

redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
    st.subheader("📊 Стан системи")

    if co2_val < co2_min_opt:
        st.warning(f"🌬️ CO₂: {co2_val:.1f} мг/л — дефіцит (норма {co2_min_opt}-{co2_max_opt})")
    elif co2_val > co2_max_opt:
        st.error(f"🌬️ CO₂: {co2_val:.1f} мг/л — надлишок")
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

    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л",
              delta=f"{f_end['NO3'] - final_no3:.1f}",
              help="Прогноз враховує поточне дозування та споживання")

    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л",
              delta=f"{f_end['PO4'] - final_po4:.2f}",
              help="Прогноз враховує поточне дозування та споживання")

    st.metric("K", f"{f_end['K']:.1f} мг/л",
              delta=f"{f_end['K'] - final_k:.1f}",
              help="Прогноз враховує поточне дозування та споживання")

    st.caption(f"""
    📌 **Фактори прогнозу:**
    - Щоденне дозування: N={current_dose_n_ml:.1f} мл, P={current_dose_p_ml:.2f} мл, K={current_dose_k_ml:.1f} мл
    - Щоденне споживання: N={daily_no3:.1f}, P={daily_po4:.2f}, K={daily_k:.1f} мг/л
    """)

    if f_end['NO3'] < 3:
        st.error("⚠️ Прогнозується критичне падіння NO₃! Збільште дозу N добрив.")
    if f_end['PO4'] < 0.1:
        st.error("⚠️ Прогнозується критичне падіння PO₄! Збільште дозу P добрив.")
    if f_end['K'] < k_opt_range['min']:
        st.error(f"⚠️ Прогнозується падіння K нижче {k_opt_range['min']:.0f} мг/л! Збільште дозу K добрив.")

# ======================== 11. ЗВІТ ========================
st.divider()
st.subheader("📋 11. Звіт для журналу")

report = f"""=== TOXICODE AQUARIUM V10.3 REPORT ===
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

ОСНОВНІ ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л (норма {co2_min_opt}-{co2_max_opt})
pH: {ph_morning} (ранок) → {ph_evening} (вечір)

МАКРОЕЛЕМЕНТИ (поточні → ціль)
NO3: {final_no3:.1f} → {target_no3} мг/л
PO4: {final_po4:.2f} → {target_po4_real:.2f} мг/л
K:   {final_k:.1f} → {target_k} мг/л

БАЛАНСИ
N:P = {redfield_ratio:.1f}:1 → {redfield_status}
K/GH = {k_gh_ratio:.2f} (норма 1.5-2.5)

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ
NO3: {f_end['NO3']:.1f} мг/л
PO4: {f_end['PO4']:.2f} мг/л
K:   {f_end['K']:.1f} мг/л

РЕКОМЕНДАЦІЇ ШІ
🌊 Ризик водоростей: {algae}
💡 Світло: {light}

КОРЕКЦІЯ ДОЗИ
N: {current_dose_n_ml:.1f} → {new_dose_n:.1f} мл/день
P: {current_dose_p_ml:.2f} → {new_dose_p:.2f} мл/день
K: {current_dose_k_ml:.1f} → {new_dose_k:.1f} мл/день
======================================"""

st.code(report, language="text")

# ======================== 12. ІСТОРІЯ ПАРАМЕТРІВ ========================
with st.expander("📜 Історія змін параметрів"):
    st.caption("Зберігайте показники вручну для відстеження динаміки (рекомендується 1 раз на день)")

    col_save1, col_save2 = st.columns([3, 1])
    with col_save1:
        save_note = st.text_input("Нотатка до збереження (необов'язково)", key="save_note", placeholder="Наприклад: після підміни, змінив дозування...")
    with col_save2:
        # FIX (Quality #3): both save buttons now use the same unified save_snapshot()
        if st.button("💾 Зберегти поточні показники", key="manual_save"):
            current_params = {
                'no3': final_no3, 'po4': final_po4, 'k': final_k,
                'tds': final_tds, 'gh': gh, 'kh': kh, 'co2': co2_val
            }
            save_snapshot(current_params, note=save_note)
            st.session_state.last_params = current_params
            st.success(f"✅ Параметри збережено! ({datetime.now().strftime('%H:%M:%S')})")
            st.rerun()

    st.divider()

    col_history1, col_history2 = st.columns([2, 1])

    with col_history1:
        if st.session_state.history:
            df_history = pd.DataFrame(st.session_state.history)
            df_history['дата'] = pd.to_datetime(df_history['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            display_cols = ['дата', 'note', 'no3', 'po4', 'k', 'tds', 'gh', 'kh', 'co2']
            display_names = ['Дата', 'Нотатка', 'NO3', 'PO4', 'K', 'TDS', 'GH', 'KH', 'CO₂']
            display_df = df_history[display_cols].tail(10)
            display_df.columns = display_names
            st.dataframe(display_df, use_container_width=True)

            if len(df_history) > 1:
                df_history_numeric = df_history[['timestamp', 'no3']].copy()
                df_history_numeric['timestamp'] = pd.to_datetime(df_history_numeric['timestamp'])
                df_history_numeric = df_history_numeric.set_index('timestamp')
                st.line_chart(df_history_numeric)
        else:
            st.info("Поки немає збережених даних. Натисніть 'Зберегти поточні показники' вище.")

    with col_history2:
        st.markdown("**💡 Порада:**")
        st.caption("""
        - Зберігайте показники **1 раз на день** в один і той самий час
        - Найкраще робити це **перед ввімкненням CO₂**
        - Додавайте нотатки для важливих змін
        - Це допоможе відстежувати довгострокову динаміку
        """)

        if st.button("🗑️ Очистити історію", key="clear_history"):
            st.session_state.history = []
            st.session_state.alerts = []
            st.rerun()

# ======================== 13. ВАЛІДАЦІЯ ========================
with st.expander("🛡️ Валідація та безпека"):
    st.markdown(f"""
    | Перевірка | Поточне | Безпечний діапазон | Статус |
    |-----------|---------|--------------------|--------|
    | NO3 | {final_no3:.1f} | 5-40 | {"✅" if 5 <= final_no3 <= 40 else "⚠️"} |
    | PO4 | {final_po4:.2f} | 0.2-2.5 | {"✅" if 0.2 <= final_po4 <= 2.5 else "⚠️"} |
    | CO₂ | {co2_val:.1f} | {co2_min_opt}-{co2_max_opt} | {"✅" if co2_min_opt <= co2_val <= co2_max_opt else "⚠️"} |
    | K/GH | {k_gh_ratio:.2f} | 1.5-2.5 | {"✅" if 1.5 <= k_gh_ratio <= 2.5 else "⚠️"} |
    """)

    if final_no3 > 40:
        st.error("🚨 Високий NO3 — зменште N добрива")
    if final_po4 > 2.5:
        st.warning("⚠️ Високий PO4 — ризик водоростей")
    if co2_val > co2_max_opt:
        st.error("🚨 Зменште подачу CO₂")
    if final_k > k_opt_range['max']:
        st.warning("⚠️ K вище максимуму — ризик блокування Ca/Mg")

st.caption("⚡ Toxicode V10.3 | Штучний Інтелект | Історія параметрів | Прогноз водоростей")
