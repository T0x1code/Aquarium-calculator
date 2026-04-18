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
    
    po4_unit = st.radio("Тест показує:", ["PO4 (фосфат)", "P (фосфор)"], horizontal=True)
    if po4_unit == "P (фосфор)":
        st.caption("⚠️ Ваші цілі будуть автоматично перераховані: P × 3.07 = PO4")
        target_po4_display = target_po4
        target_po4_real = target_po4 * 3.07
    else:
        target_po4_real = target_po4
    
    co2_min_opt = st.slider("Нижня межа CO₂ (мг/л)", 0, 100, 25)
    co2_max_opt = st.slider("Верхня межа CO₂ (мг/л)", 0, 100, 45)
    
    days = st.slider("Період прогнозу (днів)", 1, 14, 7)

# ======================== 1. РЕМІНЕРАЛІЗАТОР ========================
st.header("1. Ремінералізатор")
with st.expander("Розрахунок ремінералізації для підміни", expanded=True):
    rem_mode = st.radio("Тип ремінералізатора:", ["Ручний розрахунок (солі)", "Salty Shrimp GH+", "Quayer GH/KH+"], horizontal=True)
    
    c_vol = st.number_input("Літрів свіжої води (осмос)", value=10.0, step=5.0)
    
    if rem_mode == "Ручний розрахунок (солі)":
        target_gh = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5)
        target_kh = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5)
        target_ca_mg = st.slider("Цільове Ca:Mg", 1.0, 6.0, 3.0, 0.5)
        
        # Розрахунок солей
        kh_from_caco3 = target_kh * 17.86 * c_vol / 1000
        ca_from_caco3_g = kh_from_caco3 * 0.4
        
        total_ca_mg_mgl = target_gh * 7.14
        ratio_factor = target_ca_mg / 5.1 + 1 / 4.3
        mg_mgl = target_gh / ratio_factor
        ca_mgl = target_ca_mg * mg_mgl
        
        total_ca_g = ca_mgl * c_vol / 1000
        total_mg_g = mg_mgl * c_vol / 1000
        
        remaining_ca_g = max(0, total_ca_g - ca_from_caco3_g)
        cacl2_g = remaining_ca_g / 0.273 if remaining_ca_g > 0 else 0
        mgso4_g = total_mg_g / 0.0986 if total_mg_g > 0 else 0
        
        st.info(f"""
        **Для {c_vol:.0f} л осмосу додай:**
        - **{kh_from_caco3:.3f} г** CaCO₃ (кальцій карбонат) → KH = {target_kh:.1f}°dH
        - **{cacl2_g:.3f} г** CaCl₂·2H₂O → додатковий кальцій
        - **{mgso4_g:.3f} г** MgSO₄·7H₂O → магній
        """)
        
    elif rem_mode == "Salty Shrimp GH+":
        st.info("""
        **Salty Shrimp Bee Shrimp Mineral GH+**
        - Піднімає тільки GH, не впливає на KH
        - Дозування: 1г на 10л води = +1°dH GH
        
        **Розрахунок:**
        """)
        target_gh_only = st.slider("Потрібне підняття GH (°dH)", 0.0, 10.0, 4.0, 0.5)
        ss_dose = target_gh_only * c_vol / 10
        st.success(f"**Додай {ss_dose:.1f} г Salty Shrimp GH+ на {c_vol:.0f} л води**")
        
    else:  # Quayer GH/KH+
        st.info("""
        **QUAYER Ремінерал GH/KH+**
        - Піднімає і GH, і KH одночасно
        - Дозування: 1г на 10л води = +1°dH GH та +1°dH KH
        
        **Розрахунок:**
        """)
        target_gh_kh = st.slider("Потрібне підняття GH/KH (°dH)", 0.0, 10.0, 3.0, 0.5)
        q_dose = target_gh_kh * c_vol / 10
        st.success(f"**Додай {q_dose:.1f} г Quayer GH/KH+ на {c_vol:.0f} л води**")

# ======================== 2. КАЛЬКУЛЯТОР СПОЖИВАННЯ ========================
st.header("2. Калькулятор реального споживання")
consumption_results = {}

with st.expander("Аналіз минулого періоду"):
    st.caption("Введіть дані двох тестів (початок і зараз) та скільки добрив вносили")
    
    t1, t2, t3 = st.tabs(["NO3", "PO4", "K"])
    
    def calc_real_cons(tab, name, key_p, is_po4=False):
        with tab:
            c1, c2, c3 = st.columns(3)
            
            # Використовуємо float значення з step=0.1 або 0.01 для PO4
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
            res = (p_test * (1 - pct_wc) + added_mgl - c_test) / days_between
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"**Споживання {name}:** {val:.2f} мг/л в день")
    
    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4", is_po4=True)
    calc_real_cons(t3, "K", "k")

# ======================== 3. ПОТОЧНИЙ СТАН ========================
st.header("3. Поточні параметри води")
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
    st.caption("CO₂ контроль")
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

# ======================== 4. ПІДМІНА ВОДИ ========================
st.divider()
st.header("4. Підміна води")
c_change, c_dosing = st.columns(2)

with c_change:
    change_l = st.number_input("Літри підміни", value=50.0, step=1.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.metric("Відсоток підміни", f"{pct*100:.1f}%")
    
    weekly_change_pct = pct * 7 if pct > 0 else 0
    steady_no3 = calculate_steady_state(daily_no3, weekly_change_pct)
    st.caption(f"Steady State NO₃: {steady_no3:.0f} мг/л")

with c_dosing:
    st.markdown("**Внесення добрив ПІСЛЯ підміни:**")
    col_n, col_p, col_k = st.columns(3)
    
    with col_n:
        dose_after_n_ml = st.number_input("N мл після підміни", value=0.0, step=1.0, key="after_n")
        conc_n = st.number_input("N г/л", value=50.0, key="conc_n_after")
        add_n_after = (dose_after_n_ml * conc_n) / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_n_after:.1f} мг/л NO3")
    
    with col_p:
        dose_after_p_ml = st.number_input("P мл після підміни", value=0.0, step=0.5, key="after_p")
        conc_p = st.number_input("P г/л", value=5.0, key="conc_p_after")
        add_p_after = (dose_after_p_ml * conc_p) / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_p_after:.2f} мг/л PO4")
    
    with col_k:
        dose_after_k_ml = st.number_input("K мл після підміни", value=0.0, step=1.0, key="after_k")
        conc_k = st.number_input("K г/л", value=20.0, key="conc_k_after")
        add_k_after = (dose_after_k_ml * conc_k) / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_k_after:.1f} мг/л K")

# Розрахунок після підміни
after_no3 = no3_now * (1 - pct) + add_n_after
after_po4 = po4_now * (1 - pct) + add_p_after
after_k = k_now * (1 - pct) + add_k_after
after_tds = base_tds * (1 - pct) + (add_n_after + add_p_after + add_k_after) * 0.5

st.info(f"**Після підміни та внесення:** NO₃ = {after_no3:.1f} | PO₄ = {after_po4:.2f} | K = {after_k:.1f} | TDS = {after_tds:.0f}")

# ======================== 5. ДОЗУВАННЯ ДОБРИВ ========================
st.header("5. Дозування добрив")
st.caption("Концентрація готового розчину (г/л) та поточна доза (мл/день)")

cd_n, cd_p, cd_k = st.columns(3)

with cd_n:
    conc_n_daily = st.number_input("N (NO3) г/л", value=50.0, step=5.0, key="conc_n_daily")
    current_dose_n_ml = st.number_input("Поточна доза N мл/день", value=0.0, step=1.0, key="dose_n_daily")
    add_no3_daily = (current_dose_n_ml * conc_n_daily) / tank_vol

with cd_p:
    conc_p_daily = st.number_input("P (PO4) г/л", value=5.0, step=0.5, key="conc_p_daily")
    current_dose_p_ml = st.number_input("Поточна доза P мл/день", value=0.0, step=0.5, key="dose_p_daily")
    add_po4_daily = (current_dose_p_ml * conc_p_daily) / tank_vol

with cd_k:
    conc_k_daily = st.number_input("K г/л", value=20.0, step=2.0, key="conc_k_daily")
    current_dose_k_ml = st.number_input("Поточна доза K мл/день", value=0.0, step=1.0, key="dose_k_daily")
    add_k_daily = (current_dose_k_ml * conc_k_daily) / tank_vol

final_no3 = after_no3 + add_no3_daily
final_po4 = after_po4 + add_po4_daily
final_k = after_k + add_k_daily
final_tds = after_tds + (add_no3_daily + add_po4_daily + add_k_daily) * 0.5

# ======================== 6. ПРОГНОЗ ========================
st.header(f"6. Динамічний прогноз на {days} днів")

stability = 1 / (1 + abs((final_no3 / final_po4 if final_po4 > 0 else custom_redfield - custom_redfield) / custom_redfield))

forecast = []
curr_n, curr_p, curr_k = final_no3, final_po4, final_k

for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(0, round(curr_n, 1)),
        "PO4": max(0, round(curr_p, 2)),
        "K": max(0, round(curr_k, 1))
    })
    curr_n = max(0, curr_n + (current_dose_n_ml * conc_n_daily / tank_vol) - (daily_no3 * stability))
    curr_p = max(0, curr_p + (current_dose_p_ml * conc_p_daily / tank_vol) - (daily_po4 * stability))
    curr_k = max(0, curr_k + (current_dose_k_ml * conc_k_daily / tank_vol) - (daily_k * stability))

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)

# ======================== 7. K/GH АНАЛІЗ ========================
st.header("7. K/GH співвідношення")

k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("Як розрахувати цільовий K за GH", expanded=True):
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
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}")

with col_k3:
    if final_k < k_opt_range['min']:
        st.error(f"КРИТИЧНИЙ ДЕФІЦИТ K — підніміть на {k_opt_range['min'] - final_k:.1f} мг/л")
    elif final_k < k_opt_range['opt_low']:
        st.warning(f"Дефіцит K — підніміть до {k_opt_range['opt_low']:.0f} мг/л")
    elif final_k <= k_opt_range['opt_high']:
        st.success("✅ K в нормі")
    elif final_k <= k_opt_range['max']:
        st.warning(f"Надлишок K — знизьте на {final_k - k_opt_range['opt_high']:.1f} мг/л")
    else:
        st.error(f"КРИТИЧНИЙ НАДЛИШОК K — терміново знизьте")

# ======================== 8. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.header("8. План корекції дозування")

f_end = forecast[-1]

delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4_real - f_end["PO4"]
delta_k = target_k - f_end["K"]

if delta_no3 > 0:
    daily_delta_no3 = delta_no3 / days
    change_n_ml = (daily_delta_no3 * tank_vol) / conc_n_daily if conc_n_daily > 0 else 0
    new_dose_n = current_dose_n_ml + change_n_ml
    action_n = f"+{change_n_ml:.1f} мл/день"
elif delta_no3 < 0:
    daily_delta_no3 = abs(delta_no3) / days
    reduce_n_ml = (daily_delta_no3 * tank_vol) / conc_n_daily if conc_n_daily > 0 else 0
    new_dose_n = max(0, current_dose_n_ml - reduce_n_ml)
    action_n = f"-{reduce_n_ml:.1f} мл/день"
else:
    new_dose_n = current_dose_n_ml
    action_n = "без змін"

if delta_po4 > 0:
    daily_delta_po4 = delta_po4 / days
    change_p_ml = (daily_delta_po4 * tank_vol) / conc_p_daily if conc_p_daily > 0 else 0
    new_dose_p = current_dose_p_ml + change_p_ml
    action_p = f"+{change_p_ml:.2f} мл/день"
elif delta_po4 < 0:
    daily_delta_po4 = abs(delta_po4) / days
    reduce_p_ml = (daily_delta_po4 * tank_vol) / conc_p_daily if conc_p_daily > 0 else 0
    new_dose_p = max(0, current_dose_p_ml - reduce_p_ml)
    action_p = f"-{reduce_p_ml:.2f} мл/день"
else:
    new_dose_p = current_dose_p_ml
    action_p = "без змін"

if delta_k > 0:
    daily_delta_k = delta_k / days
    change_k_ml = (daily_delta_k * tank_vol) / conc_k_daily if conc_k_daily > 0 else 0
    new_dose_k = current_dose_k_ml + change_k_ml
    action_k = f"+{change_k_ml:.1f} мл/день"
elif delta_k < 0:
    daily_delta_k = abs(delta_k) / days
    reduce_k_ml = (daily_delta_k * tank_vol) / conc_k_daily if conc_k_daily > 0 else 0
    new_dose_k = max(0, current_dose_k_ml - reduce_k_ml)
    action_k = f"-{reduce_k_ml:.1f} мл/день"
else:
    new_dose_k = current_dose_k_ml
    action_k = "без змін"

col_rec1, col_rec2, col_rec3 = st.columns(3)

with col_rec1:
    st.metric("N доза", f"{current_dose_n_ml:.1f} → {new_dose_n:.1f} мл/день", delta=action_n)
    if delta_no3 > 0:
        st.caption(f"Дефіцит {delta_no3:.1f} мг/л за {days} днів")

with col_rec2:
    st.metric("P доза", f"{current_dose_p_ml:.2f} → {new_dose_p:.2f} мл/день", delta=action_p)
    if delta_po4 > 0:
        st.caption(f"Дефіцит {delta_po4:.2f} мг/л за {days} днів")

with col_rec3:
    st.metric("K доза", f"{current_dose_k_ml:.1f} → {new_dose_k:.1f} мл/день", delta=action_k)
    if delta_k > 0:
        st.caption(f"Дефіцит {delta_k:.1f} мг/л за {days} днів")

st.caption(f"Змінюйте дозування поступово, не більше ніж на 20% за день")

# ======================== 9. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("9. Експертний висновок")

redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
    st.subheader("Стан системи")
    
    if co2_val < co2_min_opt:
        st.warning(f"CO₂: {co2_val:.1f} мг/л — дефіцит (норма {co2_min_opt}-{co2_max_opt})")
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
    
    if final_k < k_opt_range['opt_low']:
        st.warning(f"K/GH = {k_gh_ratio:.2f} — дефіцит K")
    elif final_k > k_opt_range['opt_high']:
        st.warning(f"K/GH = {k_gh_ratio:.2f} — надлишок K")
    else:
        st.success(f"✅ K/GH = {k_gh_ratio:.2f} — норма")

with col_summary2:
    st.subheader(f"Прогноз через {days} днів")
    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л", delta=f"{f_end['NO3'] - target_no3:.1f}")
    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л", delta=f"{f_end['PO4'] - target_po4_real:.2f}")
    st.metric("K", f"{f_end['K']:.1f} мг/л", delta=f"{f_end['K'] - target_k:.1f}")

# ======================== 10. ЗВІТ ========================
st.divider()
st.subheader("10. Звіт для журналу")

report = f"""=== TOXICODE AQUARIUM V9.6 REPORT ===
Дата: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л (норма {co2_min_opt}-{co2_max_opt})
pH: {ph_morning} (ранок) → {ph_evening} (вечір)

МАКРО (поточні → ціль)
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

КОРЕКЦІЯ ДОЗИ
N: {current_dose_n_ml:.1f} → {new_dose_n:.1f} мл/день
P: {current_dose_p_ml:.2f} → {new_dose_p:.2f} мл/день
K: {current_dose_k_ml:.1f} → {new_dose_k:.1f} мл/день
====================================="""

st.code(report, language="text")

# ======================== 11. ВАЛІДАЦІЯ ========================
with st.expander("Валідація та безпека"):
    st.markdown(f"""
    | Перевірка | Поточне | Безпечний діапазон | Статус |
    |-----------|---------|--------------------|--------|
    | NO3 | {final_no3:.1f} | 5-40 | {"✅" if 5 <= final_no3 <= 40 else "⚠️"} |
    | PO4 | {final_po4:.2f} | 0.2-2.5 | {"✅" if 0.2 <= final_po4 <= 2.5 else "⚠️"} |
    | CO₂ | {co2_val:.1f} | {co2_min_opt}-{co2_max_opt} | {"✅" if co2_min_opt <= co2_val <= co2_max_opt else "⚠️"} |
    | K/GH | {k_gh_ratio:.2f} | 1.5-2.5 | {"✅" if 1.5 <= k_gh_ratio <= 2.5 else "⚠️"} |
    """)

    if final_no3 > 40:
        st.error("Високий NO3 — зменште N добрива")
    if final_po4 > 2.5:
        st.warning("Високий PO4 — ризик водоростей")
    if co2_val > co2_max_opt:
        st.error("Зменште подачу CO₂")
    if final_k > k_opt_range['max']:
        st.warning("K вище максимуму — ризик блокування Ca/Mg")

st.caption("⚡ Toxicode V9.6 | Підтримка Salty Shrimp та Quayer | Коректний розрахунок PO4")
