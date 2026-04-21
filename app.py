"""
Toxicode Aquarium System V14 — виправлення за фідбеком:
1. Інструкція в ремінералізаторі повернута
2. Калькулятор балансу — без змін (працює добре)
3. Блоки 3-5: прозора стартова точка прогнозу з поясненням
4. Симулятор: порівняльний графік для NO3 + PO4 + K
5. Waterfall — без змін
6. ШІ: рекомендації тепер пояснюють причину і дію
7. Експертний висновок (блок 10): прогноз береться з КІНЦЯ прогнозного
   горизонту, а не з поточного стану — усунено суперечність між блоками 9 і 10
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Toxicode Aquarium V14", layout="wide")
st.title("🌿 Toxicode Aquarium System V14 — Штучний Інтелект Акваріуміста")

# ======================== ІНІЦІАЛІЗАЦІЯ ========================
if 'history' not in st.session_state:
    st.session_state.history = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'last_params' not in st.session_state:
    st.session_state.last_params = None

# ======================== HELPER FUNCTIONS ========================
def clamp(v, lo, hi):
    return max(lo, min(v, hi))

def calculate_co2(kh, ph):
    try:
        val = 3 * kh * (10 ** (7 - ph))
        return round(val, 2)
    except (ValueError, OverflowError):
        return 0.0

def get_k_range(gh):
    return {
        'min':      gh * 1.2,
        'opt_low':  gh * 1.5,
        'opt_high': gh * 2.5,
        'max':      gh * 3.0,
    }

def algae_risk(no3, po4):
    if po4 <= 0:
        return "Немає даних"
    r = no3 / po4
    if r < 8:   return "🔴 Високий — дефіцит N → ціанобактерії"
    if r > 25:  return "🟠 Високий — дефіцит P → зелені водорості"
    if no3 > 30 or po4 > 1.5: return "🟡 Середній — надлишок макро"
    if no3 < 3  or po4 < 0.2: return "🟡 Середній — дефіцит макро"
    return "🟢 Низький"

def light_rec(co2, no3, po4):
    if co2 < 20 or no3 < 5 or po4 < 0.2:
        return "💡 Низьке (50-70%, 6-8 год)"
    if co2 > 30 and no3 > 10 and po4 > 0.5:
        return "⚡ Високе (90-100%, 10-12 год)"
    return "🌿 Середнє (70-90%, 8-10 год)"

def save_snapshot(params, note=""):
    record = {'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'note': note, **params}
    st.session_state.history.append(record)
    if len(st.session_state.history) > 100:
        st.session_state.history = st.session_state.history[-100:]

def check_shock(prev_val, new_val, param_name, threshold=30):
    if prev_val and prev_val > 0:
        change_pct = abs((new_val - prev_val) / prev_val * 100)
        if change_pct > threshold:
            alert = f"⚠️ Різка зміна {param_name}: {change_pct:.0f}% за один період"
            if alert not in st.session_state.alerts:
                st.session_state.alerts.append(alert)

def compute_balance(v_start, v_end, wc_frac, fert_added_mgl, dt_days):
    wc_effect = v_start * min(wc_frac, 1.0)
    expected  = v_start - wc_effect + fert_added_mgl
    invisible = v_end - expected
    dt        = max(dt_days, 0.01)
    return {
        'wc_effect':           round(wc_effect, 3),
        'fert_added':          round(fert_added_mgl, 3),
        'invisible':           round(invisible, 3),
        'consumption_per_day': round(max(0, -invisible) / dt, 3),
        'organic_per_day':     round(max(0,  invisible) / dt, 3),
    }

def run_forecast(start_no3, start_po4, start_k,
                 cons_no3, cons_po4, cons_k,
                 org_no3, org_po4, org_k,
                 fert_no3, fert_po4, fert_k,
                 wc_pct_per_day, n_days):
    rows = []
    n, p, k = start_no3, start_po4, start_k
    for d in range(n_days + 1):
        rows.append({'День': d,
                     'NO3': round(n, 2),
                     'PO4': round(p, 3),
                     'K':   round(k, 2)})
        n = clamp(n * (1 - wc_pct_per_day) + fert_no3 - cons_no3 + org_no3, 0, 500)
        p = clamp(p * (1 - wc_pct_per_day) + fert_po4 - cons_po4 + org_po4, 0, 50)
        k = clamp(k * (1 - wc_pct_per_day) + fert_k   - cons_k   + org_k,   0, 500)
    return rows

# ======================== SIDEBAR ========================
with st.sidebar:
    st.header("⚙️ Конфігурація системи")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0, min_value=1.0)

    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0,  step=0.1)
    target_k   = st.number_input("Ціль K (мг/л)",   value=15.0, step=1.0)
    target_tds = st.number_input("Ціль TDS",         value=120.0, step=5.0)

    st.divider()
    st.subheader("🔬 Розширені налаштування")
    custom_redfield = st.slider("Бажана N:P пропорція", 5, 30, 15)

    po4_unit   = st.radio("Тест показує:", ["PO4 (фосфат)", "P (фосфор)"], horizontal=True)
    po4_factor = 3.07 if po4_unit == "P (фосфор)" else 1.0
    if po4_factor != 1.0:
        st.caption("⚠️ P × 3.07 = PO4 — перерахунок автоматичний")

    co2_min_opt = st.slider("CO₂ мін (мг/л)", 0, 100, 25)
    co2_max_opt = st.slider("CO₂ макс (мг/л)", 0, 100, 45)
    days        = st.slider("Період прогнозу (днів)", 1, 30, 7)

# Алерти
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
        c_vol         = st.number_input("Літрів свіжої води (осмос)", value=10.0, step=5.0, key="rem_vol")
        st.subheader("🎯 Цільові параметри")
        target_gh     = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5)
        target_kh     = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5)
        target_ca_mg  = st.slider("Цільове Ca:Mg",      1.0,  6.0, 3.0, 0.5)
    with col_rem2:
        st.subheader("🧪 Розрахований склад")
        denom      = (target_ca_mg / 5.1) + (1.0 / 4.3)
        mg_mgl     = target_gh / denom if denom > 0 else 0
        ca_mgl     = target_ca_mg * mg_mgl
        total_ca_g = ca_mgl * c_vol / 1000
        total_mg_g = mg_mgl * c_vol / 1000
        caco3_g    = target_kh * 17.86 * c_vol / 1000
        ca_caco3_g = caco3_g * 0.4
        rem_ca_g   = max(0, total_ca_g - ca_caco3_g)
        cacl2_g    = rem_ca_g / 0.273 if rem_ca_g > 0 else 0
        mgso4_g    = total_mg_g / 0.0986 if total_mg_g > 0 else 0

        st.success(f"""
**Для {c_vol:.0f} л осмосу:**
🧂 CaCO₃: **{caco3_g:.3f} г**
🧂 CaCl₂·2H₂O: **{cacl2_g:.3f} г**
🧂 MgSO₄·7H₂O: **{mgso4_g:.3f} г**
        """)
        st.caption(f"Ca = {ca_mgl:.1f} мг/л | Mg = {mg_mgl:.1f} мг/л | TDS ~{target_gh*10+target_kh*5:.0f} ppm")
        if cacl2_g < 0.01:
            st.info("💡 CaCO₃ покриває весь Ca, CaCl₂ не потрібен.")
        elif cacl2_g > 1.0:
            st.warning("⚠️ Велика кількість CaCl₂ — перевірте параметри.")

    # FIX 1: повернута інструкція з приготування
    st.divider()
    with st.expander("📖 Інструкція приготування", expanded=False):
        st.markdown(f"""
### 📋 Покрокова інструкція

1. **Підготуйте {c_vol:.0f} л осмосу** в чистій ємності

2. **Додайте солі в такому порядку:**
   - 🧂 **CaCO₃** — важко розчиняється, додайте першим, перемішайте
   - 🧂 **MgSO₄·7H₂O** — добре розчиняється
   - 🧂 **CaCl₂·2H₂O** — додайте останнім

3. **Перемішайте** до повного розчинення (помпа або активне перемішування).  
   Для прискорення CaCO₃ можна додати трохи CO₂ або газованої води.

4. **Виміряйте TDS** — має бути ≈ {target_gh*10+target_kh*5:.0f} ppm

5. **Перевірте GH/KH тестом** (за можливості):
   - GH має бути {target_gh:.1f}°dH
   - KH має бути {target_kh:.1f}°dH

6. **Вносьте в акваріум поступово** — не більше 30% об'єму за раз,
   протягом 30–60 хвилин.

### ⚡ Важливі поради

| | |
|---|---|
| Зберігання | У закритій ємності не більше 2 тижнів |
| Температура | Кімнатна — для кращого розчинення |
| Передозування | Зробіть додаткову підміну чистою водою |
| Ca:Mg у воді | Ca = {ca_mgl:.1f} мг/л, Mg = {mg_mgl:.1f} мг/л |

### 📊 Підсумкові параметри

| Параметр | Значення |
|----------|----------|
| Об'єм | {c_vol:.0f} л |
| Цільовий GH | {target_gh:.1f}°dH |
| Цільовий KH | {target_kh:.1f}°dH |
| Ca:Mg | {target_ca_mg:.1f}:1 |
| TDS (орієнт.) | {target_gh*10+target_kh*5:.0f} ppm |
        """)

# ======================== 2. КАЛЬКУЛЯТОР БАЛАНСУ ========================
st.header("📊 2. Калькулятор реального споживання")
st.caption("""
**Як це працює:** введіть два тести з однакового акваріума з різницею в часі.
Програма враховує підміну і добрива між ними, і розкладає зміну на компоненти:
**споживання рослинами** (якщо рівень впав більше ніж очікувалось)
або **накопичення/джерело** (якщо рівень впав менше або виріс — органіка, перегодовування тощо).
""")

with st.expander("🔬 Аналіз між двома тестами", expanded=True):
    bc1, bc2 = st.columns(2)
    with bc1:
        st.subheader("📌 Початковий тест")
        b_no3_start = st.number_input("NO3 початок (мг/л)", value=15.0, step=0.5,  format="%.1f", key="b_no3s")
        b_po4_start = st.number_input("PO4 початок (мг/л)", value=1.0,  step=0.05, format="%.2f", key="b_po4s")
        b_k_start   = st.number_input("K початок (мг/л)",   value=10.0, step=0.5,  format="%.1f", key="b_ks")
        st.divider()
        st.subheader("🔁 Що відбулось між тестами")
        b_days    = st.number_input("Днів між тестами", value=7, min_value=1, step=1, key="b_days")
        b_wc_l    = st.number_input("Підміна (л, 0 якщо не було)", value=0.0, step=5.0, key="b_wcl")
        b_wc_frac = b_wc_l / tank_vol if tank_vol > 0 else 0
        if b_wc_l > 0:
            st.caption(f"= {b_wc_frac*100:.1f}% об'єму акваріума")
        st.markdown("**Добрива між тестами (загалом за весь період):**")
        bc_f1, bc_f2, bc_f3 = st.columns(3)
        with bc_f1:
            b_fert_n_ml   = st.number_input("N мл (всього)", value=0.0, step=1.0, key="b_fn_ml")
            b_fert_n_conc = st.number_input("N г/л",          value=50.0, step=5.0, key="b_fn_c")
            b_fert_n_mgl  = b_fert_n_ml * b_fert_n_conc / tank_vol if tank_vol > 0 else 0
            st.caption(f"+{b_fert_n_mgl:.2f} мг/л NO3")
        with bc_f2:
            b_fert_p_ml   = st.number_input("P мл (всього)", value=0.0, step=0.5, key="b_fp_ml")
            b_fert_p_conc = st.number_input("P г/л",          value=5.0,  step=0.5, key="b_fp_c")
            b_fert_p_mgl  = b_fert_p_ml * b_fert_p_conc / tank_vol if tank_vol > 0 else 0
            st.caption(f"+{b_fert_p_mgl:.3f} мг/л PO4")
        with bc_f3:
            b_fert_k_ml   = st.number_input("K мл (всього)", value=0.0, step=1.0, key="b_fk_ml")
            b_fert_k_conc = st.number_input("K г/л",          value=20.0, step=2.0, key="b_fk_c")
            b_fert_k_mgl  = b_fert_k_ml * b_fert_k_conc / tank_vol if tank_vol > 0 else 0
            st.caption(f"+{b_fert_k_mgl:.2f} мг/л K")

    with bc2:
        st.subheader("📌 Кінцевий тест")
        b_no3_end = st.number_input("NO3 зараз (мг/л)", value=10.0, step=0.5,  format="%.1f", key="b_no3e")
        b_po4_end = st.number_input("PO4 зараз (мг/л)", value=0.7,  step=0.05, format="%.2f", key="b_po4e")
        b_k_end   = st.number_input("K зараз (мг/л)",   value=8.0,  step=0.5,  format="%.1f", key="b_ke")

        st.divider()
        st.subheader("📊 Результат аналізу")

        bal_no3 = compute_balance(b_no3_start, b_no3_end, b_wc_frac, b_fert_n_mgl, b_days)
        bal_po4 = compute_balance(b_po4_start, b_po4_end, b_wc_frac, b_fert_p_mgl, b_days)
        bal_k   = compute_balance(b_k_start,   b_k_end,   b_wc_frac, b_fert_k_mgl, b_days)

        for label, bal, start, end in [
            ("NO3", bal_no3, b_no3_start, b_no3_end),
            ("PO4", bal_po4, b_po4_start, b_po4_end),
            ("K",   bal_k,   b_k_start,   b_k_end),
        ]:
            net = end - start
            st.markdown(f"**{label}:** {start} → {end} мг/л  (зміна: {net:+.2f})")
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("Підміна вивела",  f"−{bal['wc_effect']:.2f}")
            rc2.metric("Добрива додали",  f"+{bal['fert_added']:.2f}")
            rc3.metric("Невидима зміна",  f"{bal['invisible']:+.2f}",
                       help="від'ємна = рослини з'їли більше очікуваного; додатна = органіка/джерело")
            if bal['consumption_per_day'] > 0:
                st.success(f"✅ Споживання рослинами: **{bal['consumption_per_day']:.3f} мг/л/день**")
            if bal['organic_per_day'] > 0:
                st.warning(f"⚠️ Накопичення/джерело: **+{bal['organic_per_day']:.3f} мг/л/день**")
                if label == "NO3":
                    st.caption("Можливо: органіка, перегодовування риб, стара субстрат, недостатня підміна")
            st.caption(
                f"Рівняння: {start} − {bal['wc_effect']:.2f}(підміна) "
                f"+ {bal['fert_added']:.2f}(добриво) "
                f"{bal['invisible']:+.2f}(невидима) = {end}"
            )
            st.divider()

# ======================== 3. ПОТОЧНІ ПАРАМЕТРИ ========================
st.header("📋 3. Поточні параметри води")
st.caption("Введіть **актуальні показники тесту** на сьогодні. Ці значення є стартовою точкою для прогнозу.")
col1, col2, col3 = st.columns(3)
with col1:
    no3_now = st.number_input("NO3 (мг/л)", value=10.0, step=0.5, format="%.1f")
    if po4_unit == "P (фосфор)":
        po4_raw = st.number_input("P (мг/л)", value=0.3, step=0.05, format="%.2f")
        po4_now = round(po4_raw * po4_factor, 3)
        st.caption(f"PO4 = {po4_now:.2f} мг/л")
    else:
        po4_now = st.number_input("PO4 (мг/л)", value=0.5, step=0.05, format="%.2f")
    k_now    = st.number_input("K (мг/л)",   value=10.0, step=0.5, format="%.1f")
    base_tds = st.number_input("TDS",         value=150.0, step=5.0, format="%.0f")
with col2:
    gh = st.number_input("GH (°dH)", value=6, step=1)
    kh = st.number_input("KH (°dH)", value=2, step=1)
    st.divider()
    st.caption("🌬️ CO₂ контроль")
    ph_morning = st.number_input("pH ранок (до CO₂)",  value=7.2, step=0.1, format="%.1f")
    ph_evening = st.number_input("pH вечір (через CO₂)", value=6.8, step=0.1, format="%.1f")
    co2_val = calculate_co2(kh, ph_evening)
    # FIX: CO2 відображення зі статусом норми
    if co2_val < co2_min_opt:
        st.metric("Розрахунковий CO₂", f"{co2_val:.1f} мг/л", delta=f"нижче норми ({co2_min_opt}–{co2_max_opt})", delta_color="inverse")
    elif co2_val > co2_max_opt:
        st.metric("Розрахунковий CO₂", f"{co2_val:.1f} мг/л", delta=f"вище норми! ({co2_min_opt}–{co2_max_opt})", delta_color="inverse")
    else:
        st.metric("Розрахунковий CO₂", f"{co2_val:.1f} мг/л", delta="✅ в нормі", delta_color="off")
with col3:
    st.subheader("📥 Споживання і джерела")
    st.caption("Автозаповнення з розділу 2. Можна змінити вручну.")
    default_cons_no3 = bal_no3['consumption_per_day'] if bal_no3['consumption_per_day'] > 0 else 2.0
    default_cons_po4 = bal_po4['consumption_per_day'] if bal_po4['consumption_per_day'] > 0 else 0.1
    default_cons_k   = bal_k['consumption_per_day']   if bal_k['consumption_per_day']   > 0 else 1.0
    default_org_no3  = bal_no3['organic_per_day']
    default_org_po4  = bal_po4['organic_per_day']
    default_org_k    = bal_k['organic_per_day']

    daily_no3 = st.number_input("Споживання NO3 (мг/л/день)", value=float(default_cons_no3), step=0.1,  format="%.2f")
    daily_po4 = st.number_input("Споживання PO4 (мг/л/день)", value=float(default_cons_po4), step=0.01, format="%.3f")
    daily_k   = st.number_input("Споживання K (мг/л/день)",   value=float(default_cons_k),   step=0.1,  format="%.2f")
    st.divider()
    st.caption("⚗️ Джерело накопичення (органіка, блокування):")
    org_no3 = st.number_input("Джерело NO3 (мг/л/день)", value=float(default_org_no3), step=0.05, format="%.3f",
                               help="Якщо NO3 росте без внесення — вкажіть темп зростання з розділу 2")
    org_po4 = st.number_input("Джерело PO4 (мг/л/день)", value=float(default_org_po4), step=0.01, format="%.3f")
    org_k   = st.number_input("Джерело K (мг/л/день)",   value=float(default_org_k),   step=0.05, format="%.3f")

if st.session_state.last_params:
    lp = st.session_state.last_params
    check_shock(lp.get('no3'), no3_now, "NO₃")
    check_shock(lp.get('po4'), po4_now, "PO₄")
    check_shock(lp.get('k'),   k_now,   "K")

# ======================== 4. ПІДМІНА ВОДИ ========================
st.divider()
st.header("💧 4. Підміна води")
st.caption("Введіть дані **планової або останньої** підміни. Якщо підміни ще не було — залишайте 0 і додайте лише добрива.")
c_change, c_dosing = st.columns(2)
with c_change:
    change_l = st.number_input("Літри підміни (0 якщо не планується)", value=50.0, step=1.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.metric("Відсоток підміни", f"{pct*100:.1f}%")
    st.caption("Параметри свіжої води (якщо осмос — залишайте 0):")
    wc_col1, wc_col2, wc_col3 = st.columns(3)
    wc_no3_fresh = wc_col1.number_input("NO3 свіжої", value=0.0, step=0.5,  key="wc_no3f")
    wc_po4_fresh = wc_col2.number_input("PO4 свіжої", value=0.0, step=0.05, key="wc_po4f")
    wc_k_fresh   = wc_col3.number_input("K свіжої",   value=0.0, step=0.5,  key="wc_kf")
with c_dosing:
    st.markdown("**➕ Внесення добрив ПІСЛЯ підміни (разово):**")
    col_n, col_p, col_k_d = st.columns(3)
    with col_n:
        dose_after_n_ml = st.number_input("N мл", value=0.0, step=1.0,  key="after_n")
        conc_n_after    = st.number_input("N г/л", value=50.0,          key="conc_n_after")
        add_n_after     = dose_after_n_ml * conc_n_after / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_n_after:.2f} мг/л NO3")
    with col_p:
        dose_after_p_ml = st.number_input("P мл", value=0.0, step=0.5,  key="after_p")
        conc_p_after    = st.number_input("P г/л", value=5.0,           key="conc_p_after")
        add_p_after     = dose_after_p_ml * conc_p_after / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_p_after:.3f} мг/л PO4")
    with col_k_d:
        dose_after_k_ml = st.number_input("K мл", value=0.0, step=1.0,  key="after_k")
        conc_k_after    = st.number_input("K г/л", value=20.0,          key="conc_k_after")
        add_k_after     = dose_after_k_ml * conc_k_after / tank_vol if tank_vol > 0 else 0
        st.caption(f"+{add_k_after:.2f} мг/л K")

# Розрахунок після підміни + одноразового добрива
after_no3 = no3_now * (1 - pct) + wc_no3_fresh * pct + add_n_after
after_po4 = po4_now * (1 - pct) + wc_po4_fresh * pct + add_p_after
after_k   = k_now   * (1 - pct) + wc_k_fresh   * pct + add_k_after
after_tds = base_tds * (1 - pct) + (add_n_after + add_p_after + add_k_after) * 0.5

st.info(f"**📈 Після підміни + одноразового добрива:** NO₃ = {after_no3:.1f} | PO₄ = {after_po4:.2f} | K = {after_k:.1f} | TDS = {after_tds:.0f}")

# ======================== 5. ЩОДЕННЕ ДОЗУВАННЯ ========================
st.header("🧪 5. Щоденне дозування добрив")
st.caption("Введіть **щоденну** дозу. Ці значення використовуються в прогнозі для кожного дня.")
cd_n, cd_p, cd_k = st.columns(3)
with cd_n:
    conc_n_daily      = st.number_input("N (NO3) г/л", value=50.0, step=5.0, key="conc_n_daily")
    current_dose_n_ml = st.number_input("Доза N мл/день", value=0.0, step=1.0, key="dose_n_daily")
    add_no3_daily     = current_dose_n_ml * conc_n_daily / tank_vol if tank_vol > 0 else 0
    st.caption(f"→ +{add_no3_daily:.2f} мг/л NO3/день")
with cd_p:
    conc_p_daily      = st.number_input("P (PO4) г/л", value=5.0, step=0.5, key="conc_p_daily")
    current_dose_p_ml = st.number_input("Доза P мл/день", value=0.0, step=0.5, key="dose_p_daily")
    add_po4_daily     = current_dose_p_ml * conc_p_daily / tank_vol if tank_vol > 0 else 0
    st.caption(f"→ +{add_po4_daily:.3f} мг/л PO4/день")
with cd_k:
    conc_k_daily      = st.number_input("K г/л", value=20.0, step=2.0, key="conc_k_daily")
    current_dose_k_ml = st.number_input("Доза K мл/день", value=0.0, step=1.0, key="dose_k_daily")
    add_k_daily       = current_dose_k_ml * conc_k_daily / tank_vol if tank_vol > 0 else 0
    st.caption(f"→ +{add_k_daily:.2f} мг/л K/день")

# FIX 3: стартова точка прогнозу = після підміни (ДЕНЬ 0)
# Щоденне дозування починає діяти з дня 1, тому початок = after (до першого добрива)
final_no3 = after_no3
final_po4 = after_po4
final_k   = after_k
final_tds = after_tds

st.info(
    f"**📊 Стартова точка прогнозу (день 0):** "
    f"NO₃ = {final_no3:.1f} | PO₄ = {final_po4:.2f} | K = {final_k:.1f} | TDS = {final_tds:.0f}  \n"
    f"*(щоденне дозування +{add_no3_daily:.2f}/{add_po4_daily:.3f}/{add_k_daily:.2f} мг/л додається починаючи з дня 1)*"
)

# ======================== 6. ПРОГНОЗ + СИМУЛЯТОР ========================
st.header(f"📈 6. Динамічний прогноз на {days} днів")

# Підміна: рівномірно розподіляємо тижневий відсоток по днях
wc_weekly_pct = pct  # підміна одна за тиждень
wc_daily_frac = wc_weekly_pct / 7  # рівномірно щодня

forecast = run_forecast(
    final_no3, final_po4, final_k,
    daily_no3, daily_po4, daily_k,
    org_no3,   org_po4,   org_k,
    add_no3_daily, add_po4_daily, add_k_daily,
    wc_daily_frac, days
)
df_fc = pd.DataFrame(forecast).set_index("День")
f_end = forecast[-1]

k_range = get_k_range(gh)

# FIX 4: симулятор показує NO3 + PO4 + K на одному графіку через нормалізацію
with st.expander("🔬 Симулятор «Що якщо»", expanded=False):
    st.caption("Змінюйте параметри — прогноз оновлюється миттєво. Порівняння: поточне vs сценарій.")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sim_n  = sc1.slider("N мл/день",       0.0, 30.0, float(current_dose_n_ml), 0.5, key="sim_n")
    sim_p  = sc2.slider("P мл/день",       0.0, 20.0, float(current_dose_p_ml), 0.1, key="sim_p")
    sim_k  = sc3.slider("K мл/день",       0.0, 30.0, float(current_dose_k_ml), 0.5, key="sim_k")
    sim_wc = sc4.slider("Підміна %/тижд.", 0,   80,   int(wc_weekly_pct * 100), 5,   key="sim_wc")

    sim_fc = run_forecast(
        final_no3, final_po4, final_k,
        daily_no3, daily_po4, daily_k,
        org_no3, org_po4, org_k,
        sim_n * conc_n_daily / tank_vol if tank_vol > 0 else 0,
        sim_p * conc_p_daily / tank_vol if tank_vol > 0 else 0,
        sim_k * conc_k_daily / tank_vol if tank_vol > 0 else 0,
        (sim_wc / 100) / 7, days
    )
    df_sim = pd.DataFrame(sim_fc).set_index("День")

    # Порівняльні графіки для всіх трьох елементів
    sim_tab1, sim_tab2, sim_tab3 = st.tabs(["NO3", "PO4", "K"])
    with sim_tab1:
        df_cmp_n = df_fc[["NO3"]].rename(columns={"NO3": "NO3 (поточне)"})
        df_cmp_n["NO3 (сценарій)"] = df_sim["NO3"]
        st.line_chart(df_cmp_n)
    with sim_tab2:
        df_cmp_p = df_fc[["PO4"]].rename(columns={"PO4": "PO4 (поточне)"})
        df_cmp_p["PO4 (сценарій)"] = df_sim["PO4"]
        st.line_chart(df_cmp_p)
    with sim_tab3:
        df_cmp_k = df_fc[["K"]].rename(columns={"K": "K (поточне)"})
        df_cmp_k["K (сценарій)"] = df_sim["K"]
        st.line_chart(df_cmp_k)

    se = sim_fc[-1]
    m1, m2, m3 = st.columns(3)
    m1.metric(f"NO3 день {days}", f"{se['NO3']:.1f}", delta=f"{se['NO3']-f_end['NO3']:+.1f} vs поточне")
    m2.metric(f"PO4 день {days}", f"{se['PO4']:.2f}", delta=f"{se['PO4']-f_end['PO4']:+.2f} vs поточне")
    m3.metric(f"K день {days}",   f"{se['K']:.1f}",   delta=f"{se['K']-f_end['K']:+.1f} vs поточне")

st.subheader("📊 Поточний прогноз")
st.line_chart(df_fc)

if f_end['NO3'] < 3:
    st.error(f"⚠️ День {days}: NO3 впаде до {f_end['NO3']:.1f} мг/л — критично!")
if f_end['PO4'] < 0.1:
    st.error(f"⚠️ День {days}: PO4 впаде до {f_end['PO4']:.2f} мг/л — критично!")
if f_end['K'] < k_range['min']:
    st.error(f"⚠️ День {days}: K впаде до {f_end['K']:.1f} мг/л — нижче мінімуму!")
if f_end['NO3'] > 40:
    st.warning(f"⚠️ День {days}: NO3 перевищить 40 мг/л.")

# Waterfall
with st.expander("🌊 Waterfall — баланс за тиждень"):
    wf_sel = st.selectbox("Елемент:", ["NO3", "PO4", "K"], key="wf_sel")
    pmap = {
        "NO3": (final_no3, daily_no3, add_no3_daily, org_no3),
        "PO4": (final_po4, daily_po4, add_po4_daily, org_po4),
        "K":   (final_k,   daily_k,   add_k_daily,   org_k),
    }
    sv, cv, fv, ov = pmap[wf_sel]
    wc_7   = sv * wc_daily_frac * 7
    cons_7 = cv * 7
    fert_7 = fv * 7
    org_7  = ov * 7
    end_7  = sv - wc_7 - cons_7 + fert_7 + org_7

    wfw1, wfw2 = st.columns([2, 1])
    with wfw1:
        wf_df = pd.DataFrame({
            "Компонент": ["Початок тижня", "− Підміна", "− Споживання", "+ Добрива", "+ Органіка/джерело"],
            "мг/л":      [sv, -wc_7, -cons_7, fert_7, org_7]
        }).set_index("Компонент")
        st.bar_chart(wf_df)
    with wfw2:
        st.metric("Початок",        f"{sv:.2f} мг/л")
        st.metric("− Підміна",      f"−{wc_7:.2f}")
        st.metric("− Споживання",   f"−{cons_7:.2f}")
        st.metric("+ Добрива",      f"+{fert_7:.2f}")
        st.metric("+ Органіка",     f"+{org_7:.2f}")
        st.metric("= Кінець тижня", f"{end_7:.2f} мг/л", delta=f"{end_7-sv:+.2f}")

# ======================== 7. K/GH АНАЛІЗ ========================
st.header("🧂 7. K/GH співвідношення")
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("📐 Аналіз K/GH", expanded=True):
    st.caption(f"Для GH={gh}°dH: мін {k_range['min']:.1f} | оптимум {k_range['opt_low']:.0f}–{k_range['opt_high']:.0f} | макс {k_range['max']:.1f} мг/л")
    ck1, ck2, ck3 = st.columns(3)
    ck1.metric("Поточний K", f"{final_k:.1f} мг/л")
    ck2.metric("K/GH ratio", f"{k_gh_ratio:.2f}", delta="норма 1.5–2.5")
    with ck3:
        if   final_k < k_range['min']:       st.error("🔴 Критичний дефіцит K")
        elif final_k < k_range['opt_low']:   st.warning(f"🟡 Дефіцит — підніміть до {k_range['opt_low']:.0f} мг/л")
        elif final_k <= k_range['opt_high']: st.success("✅ K в нормі")
        elif final_k <= k_range['max']:      st.warning(f"🟡 Надлишок — знизьте на {final_k-k_range['opt_high']:.1f} мг/л")
        else:                                st.error("🔴 Критичний надлишок K")

    k_fc = []
    kv = final_k
    for d in range(days + 1):
        k_fc.append({'День': d, 'K (прогноз)': round(kv, 2),
                     'Оптимум мін': k_range['opt_low'],
                     'Оптимум макс': k_range['opt_high']})
        kv = clamp(kv * (1 - wc_daily_frac) + add_k_daily - daily_k + org_k, 0, 500)
    st.line_chart(pd.DataFrame(k_fc).set_index("День"))
    if k_fc[-1]['K (прогноз)'] < k_range['opt_low']:
        st.warning(f"📉 Через {days} днів K = {k_fc[-1]['K (прогноз)']:.1f} мг/л — нижче оптимуму. Збільшіть дозу K.")

# ======================== 8. ШІ АНАЛІЗ ========================
st.header("🤖 8. Штучний Інтелект — Аналіз та рекомендації")

st.info(f"**🌊 Ризик водоростей:** {algae_risk(final_no3, final_po4)}")
st.info(f"**💡 Рекомендація по світлу:** {light_rec(co2_val, final_no3, final_po4)}")

npk_total = final_no3 + final_po4 + final_k
if npk_total > 0:
    st.caption(f"**📊 NPK частки:** N={final_no3/npk_total:.2f} : P={final_po4/npk_total:.2f} : K={final_k/npk_total:.2f}")

st.subheader("💡 Поточні рекомендації")
# FIX 6: рекомендації тепер пояснюють і причину, і конкретну дію
recs = []

# NO3
if final_no3 < 5:
    recs.append(("error",
        f"NO3 критично низький ({final_no3:.1f} мг/л). "
        f"Збільшіть щоденну дозу N або зменшіть підміну. "
        f"Ціль: {target_no3} мг/л."))
elif final_no3 < 10:
    recs.append(("warning",
        f"NO3 низький ({final_no3:.1f} мг/л) — може гальмувати ріст рослин. "
        f"Збільшіть дозу N на ~20%. Ціль: {target_no3} мг/л."))
elif final_no3 > 40:
    recs.append(("error",
        f"NO3 дуже високий ({final_no3:.1f} мг/л) — ризик водоростей. "
        f"Зменшіть дозу N або збільшіть підміну."))
elif final_no3 > 30:
    recs.append(("warning",
        f"NO3 підвищений ({final_no3:.1f} мг/л). Зменшіть N на 10–20%."))

if org_no3 > 0.3:
    recs.append(("warning",
        f"NO3 накопичується (+{org_no3:.2f} мг/л/день) без внесення добрив. "
        f"Можливі причини: розкладання органіки, перегодовування риб, стара субстрат. "
        f"Збільшіть підміни або приберіть органіку."))

# PO4
if final_po4 < 0.2:
    recs.append(("error",
        f"PO4 критично низький ({final_po4:.2f} мг/л) — рослини голодують. "
        f"Збільшіть дозу P. Ціль: {target_po4} мг/л."))
elif final_po4 < 0.5:
    recs.append(("warning",
        f"PO4 низький ({final_po4:.2f} мг/л) — фосфор може бути лімітуючим фактором. "
        f"Розгляньте збільшення P."))
elif final_po4 > 2.5:
    recs.append(("error",
        f"PO4 дуже високий ({final_po4:.2f} мг/л) — прямий ризик водоростей. "
        f"Зменшіть дозу P і збільшіть підміну."))
elif final_po4 > 1.5:
    recs.append(("warning",
        f"PO4 підвищений ({final_po4:.2f} мг/л). Слідкуйте за водоростями."))

# K
if final_k < k_range['opt_low']:
    recs.append(("error",
        f"K дефіцит ({final_k:.1f} мг/л, норма ≥{k_range['opt_low']:.0f}). "
        f"Збільшіть дозу K."))
elif final_k > k_range['opt_high']:
    recs.append(("warning",
        f"K надлишок ({final_k:.1f} мг/л, норма ≤{k_range['opt_high']:.0f}). "
        f"Можливе блокування Ca/Mg — зменшіть K."))

# CO2
if co2_val < co2_min_opt:
    recs.append(("error",
        f"CO₂ дефіцит ({co2_val:.1f} мг/л, норма {co2_min_opt}–{co2_max_opt}). "
        f"Збільшіть подачу CO₂ або покращіть розчинення."))
elif co2_val > co2_max_opt:
    recs.append(("error",
        f"CO₂ надлишок ({co2_val:.1f} мг/л) — ризик загибелі риб! "
        f"Негайно зменшіть подачу і провітріть акваріум."))

# N:P
if final_po4 > 0:
    np_r = final_no3 / final_po4
    if np_r < custom_redfield * 0.8:
        recs.append(("warning",
            f"N:P = {np_r:.1f}:1 (ціль {custom_redfield}:1) — дефіцит азоту відносно фосфору. "
            f"Збільшіть дозу N або зменшіть P."))
    elif np_r > custom_redfield * 1.2:
        recs.append(("warning",
            f"N:P = {np_r:.1f}:1 (ціль {custom_redfield}:1) — дефіцит фосфору відносно азоту. "
            f"Збільшіть дозу P або зменшіть N."))

if recs:
    for level, msg in recs[:6]:
        if level == "error":
            st.error(f"🔴 {msg}")
        else:
            st.warning(f"🟡 {msg}")
else:
    st.success("✅ Всі параметри в оптимальному діапазоні!")

# ======================== 9. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.header("📅 9. План корекції дозування")
st.caption(f"Розраховано для досягнення цілей через {days} днів, виходячи з прогнозованих значень на день {days}.")

def dose_correction(target, forecast_end_val, days_n, conc, current_ml, tv):
    """Коригує дозу щоб за days_n днів досягти target."""
    delta = target - forecast_end_val
    if abs(delta) < 0.5:
        return current_ml, "без змін"
    daily_delta = abs(delta) / max(days_n, 1)
    change_ml   = daily_delta * tv / conc if conc > 0 else 0
    if delta > 0:
        return current_ml + change_ml, f"+{change_ml:.2f} мл/день"
    return max(0, current_ml - change_ml), f"-{change_ml:.2f} мл/день"

new_n, act_n = dose_correction(target_no3, f_end['NO3'], days, conc_n_daily, current_dose_n_ml, tank_vol)
new_p, act_p = dose_correction(target_po4, f_end['PO4'], days, conc_p_daily, current_dose_p_ml, tank_vol)
new_k, act_k = dose_correction(target_k,   f_end['K'],   days, conc_k_daily, current_dose_k_ml, tank_vol)

cr1, cr2, cr3 = st.columns(3)
cr1.metric("N доза", f"{current_dose_n_ml:.1f} → {new_n:.1f} мл/день", delta=act_n)
cr2.metric("P доза", f"{current_dose_p_ml:.2f} → {new_p:.2f} мл/день", delta=act_p)
cr3.metric("K доза", f"{current_dose_k_ml:.1f} → {new_k:.1f} мл/день", delta=act_k)
st.caption("💡 Змінюйте поступово — не більше 20% за раз")

# ======================== 10. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("📝 10. Експертний висновок")

# FIX 7: блок 10 тепер явно розділяє поточний стан (з тесту) і прогноз (з кінця forecast)
# Це усуває суперечність: блок 9 показував обнулення (з прогнозу), а блок 10 показував
# поточні значення — вони природно відрізнялись і вводили в оману

redfield_status = "баланс"
redfield_ratio  = 0.0
if final_po4 > 0:
    redfield_ratio = final_no3 / final_po4
    if redfield_ratio < custom_redfield * 0.8:
        redfield_status = "дефіцит N"
    elif redfield_ratio > custom_redfield * 1.2:
        redfield_status = "дефіцит P"

# Редфілд на кінець прогнозу
redfield_forecast = "баланс"
redfield_ratio_fc = 0.0
if f_end['PO4'] > 0:
    redfield_ratio_fc = f_end['NO3'] / f_end['PO4']
    if redfield_ratio_fc < custom_redfield * 0.8:
        redfield_forecast = "дефіцит N"
    elif redfield_ratio_fc > custom_redfield * 1.2:
        redfield_forecast = "дефіцит P"

col_s1, col_s2 = st.columns(2)
with col_s1:
    st.subheader("📊 Поточний стан (з тесту)")
    st.caption(f"NO3={final_no3:.1f} | PO4={final_po4:.2f} | K={final_k:.1f} мг/л")

    if co2_val < co2_min_opt:
        st.warning(f"🌬️ CO₂: {co2_val:.1f} — дефіцит (норма {co2_min_opt}–{co2_max_opt})")
    elif co2_val > co2_max_opt:
        st.error(f"🌬️ CO₂: {co2_val:.1f} — надлишок!")
    else:
        st.success(f"✅ CO₂: {co2_val:.1f} мг/л — норма")

    if redfield_status == "дефіцит N":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — дефіцит N (ціль {custom_redfield}:1)")
    elif redfield_status == "дефіцит P":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — дефіцит P (ціль {custom_redfield}:1)")
    else:
        st.success(f"✅ N:P = {redfield_ratio:.1f}:1 — баланс")

    k_gh_now = final_k / gh if gh > 0 else 0
    if final_k < k_range['opt_low']:
        st.warning(f"⚠️ K/GH = {k_gh_now:.2f} — дефіцит K")
    elif final_k > k_range['opt_high']:
        st.warning(f"⚠️ K/GH = {k_gh_now:.2f} — надлишок K")
    else:
        st.success(f"✅ K/GH = {k_gh_now:.2f} — норма")

with col_s2:
    st.subheader(f"📈 Прогноз через {days} днів")
    st.caption(f"NO3={f_end['NO3']:.1f} | PO4={f_end['PO4']:.2f} | K={f_end['K']:.1f} мг/л  *(при незмінному дозуванні)*")

    # Метрики показують зміну від поточного до прогнозованого
    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л",
              delta=f"{f_end['NO3']-final_no3:.1f} (ціль {target_no3})",
              delta_color="normal" if abs(f_end['NO3'] - target_no3) < 5 else "inverse")
    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л",
              delta=f"{f_end['PO4']-final_po4:.2f} (ціль {target_po4})",
              delta_color="normal" if abs(f_end['PO4'] - target_po4) < 0.3 else "inverse")
    st.metric("K",   f"{f_end['K']:.1f} мг/л",
              delta=f"{f_end['K']-final_k:.1f} (ціль {target_k})",
              delta_color="normal" if abs(f_end['K'] - target_k) < 3 else "inverse")

    # Статус прогнозу
    if redfield_forecast == "дефіцит N":
        st.warning(f"⚠️ N:P через {days}д = {redfield_ratio_fc:.1f}:1 — дефіцит N")
    elif redfield_forecast == "дефіцит P":
        st.warning(f"⚠️ N:P через {days}д = {redfield_ratio_fc:.1f}:1 — дефіцит P")
    else:
        st.success(f"✅ N:P через {days}д = {redfield_ratio_fc:.1f}:1 — баланс")

    if f_end['NO3'] < 3:   st.error("🚨 NO₃ впаде критично низько!")
    if f_end['PO4'] < 0.1: st.error("🚨 PO₄ впаде критично низько!")
    if f_end['K'] < k_range['min']:
        st.error(f"🚨 K впаде нижче мінімуму {k_range['min']:.0f} мг/л!")

    # Підказка щодо плану корекції
    if act_n != "без змін" or act_p != "без змін" or act_k != "без змін":
        st.info(
            f"💡 Для досягнення цілей за {days} днів — скоригуйте дози "
            f"(розділ 9): N {act_n}, P {act_p}, K {act_k}"
        )
    else:
        st.success("✅ Поточне дозування веде до цілей!")

# ======================== 11. ЗВІТ ========================
st.divider()
st.subheader("📋 11. Звіт для журналу")
report = f"""=== TOXICODE AQUARIUM V14 ===
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

ПАРАМЕТРИ
Об'єм: {tank_vol} л | GH: {gh}°dH | KH: {kh}°dH | TDS: {final_tds:.0f}
CO₂: {co2_val:.1f} мг/л (норма {co2_min_opt}–{co2_max_opt}) | pH: {ph_morning}→{ph_evening}

ПОТОЧНІ ПАРАМЕТРИ (з тесту)
NO3: {final_no3:.1f}  PO4: {final_po4:.2f}  K: {final_k:.1f} мг/л
N:P = {redfield_ratio:.1f}:1 ({redfield_status}) | K/GH = {k_gh_ratio:.2f}

БАЛАНС (споживання / джерело мг/л/день)
NO3: −{daily_no3:.2f} / +{org_no3:.3f}
PO4: −{daily_po4:.3f} / +{org_po4:.3f}
K:   −{daily_k:.2f} / +{org_k:.3f}

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ (при поточному дозуванні)
NO3: {f_end['NO3']:.1f}  PO4: {f_end['PO4']:.2f}  K: {f_end['K']:.1f} мг/л
N:P через {days}д = {redfield_ratio_fc:.1f}:1 ({redfield_forecast})

{algae_risk(final_no3, final_po4)}

КОРЕКЦІЯ ДОЗИ (для досягнення цілей)
N: {current_dose_n_ml:.1f}→{new_n:.1f} мл/день ({act_n})
P: {current_dose_p_ml:.2f}→{new_p:.2f} мл/день ({act_p})
K: {current_dose_k_ml:.1f}→{new_k:.1f} мл/день ({act_k})
=============================="""
st.code(report, language="text")

# ======================== 12. ІСТОРІЯ ========================
with st.expander("📜 12. Історія параметрів"):
    col_save1, col_save2 = st.columns([3, 1])
    with col_save1:
        save_note = st.text_input("Нотатка", key="save_note",
                                  placeholder="Наприклад: після підміни, змінив дозування...")
    with col_save2:
        if st.button("💾 Зберегти показники", key="manual_save"):
            params = {
                'no3': final_no3, 'po4': final_po4, 'k': final_k,
                'tds': final_tds, 'gh': gh, 'kh': kh, 'co2': co2_val,
                'cons_no3': daily_no3, 'cons_po4': daily_po4, 'cons_k': daily_k,
                'org_no3': org_no3, 'org_po4': org_po4, 'org_k': org_k,
            }
            save_snapshot(params, note=save_note)
            st.session_state.last_params = params
            st.success(f"✅ Збережено ({datetime.now().strftime('%H:%M:%S')})")
            st.rerun()

    if st.session_state.history:
        df_h = pd.DataFrame(st.session_state.history)
        df_h['дата'] = pd.to_datetime(df_h['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        disp = [c for c in ['дата','note','no3','po4','k','tds','co2'] if c in df_h.columns]
        st.dataframe(df_h[disp].tail(10).rename(columns={
            'дата':'Дата','note':'Нотатка','no3':'NO3','po4':'PO4',
            'k':'K','tds':'TDS','co2':'CO₂'}), use_container_width=True)

        if len(df_h) > 1:
            st.subheader("📈 Динаміка")
            chart_params = st.multiselect("Показати:", ["no3","po4","k","co2"],
                                          default=["no3","po4","k"], key="hist_chart")
            if chart_params:
                df_h['ts'] = pd.to_datetime(df_h['timestamp'])
                st.line_chart(df_h.set_index('ts')[chart_params])

            st.subheader("🔍 Детектор дрейфу")
            dr1, dr2, dr3 = st.columns(3)
            for col_d, (param, label) in zip([dr1, dr2, dr3],
                                              [('no3','NO3'), ('po4','PO4'), ('k','K')]):
                recent = df_h[param].tail(5).values.astype(float)
                if len(recent) >= 3:
                    slope = np.polyfit(range(len(recent)), recent, 1)[0]
                    std   = np.std(recent)
                    if std > 0.01 and slope > std * 0.3:
                        col_d.warning(f"📈 {label} стабільно росте")
                    elif std > 0.01 and slope < -std * 0.3:
                        col_d.warning(f"📉 {label} стабільно падає")
                    else:
                        col_d.success(f"✅ {label} стабільний")
                else:
                    col_d.caption(f"{label}: потрібно ≥3 записи")

        if st.button("🗑️ Очистити історію", key="clear_history"):
            st.session_state.history = []
            st.session_state.alerts  = []
            st.rerun()
    else:
        st.info("Немає збережених даних.")

# ======================== 13. ТЕПЛОВА КАРТА ========================
with st.expander("🌡️ 13. Теплова карта прогнозу"):
    k_r    = get_k_range(gh)
    limits = {'NO3': (5, 30), 'PO4': (0.2, 1.5), 'K': (k_r['opt_low'], k_r['opt_high'])}
    hm_em  = {}
    for col_hm, (lo, hi) in limits.items():
        emojis = []
        for rec in forecast:
            v = rec[col_hm]
            if   v < lo * 0.6: emojis.append("🔴 критич. дефіцит")
            elif v < lo:        emojis.append("🟡 дефіцит")
            elif v <= hi:       emojis.append("🟢 норма")
            elif v <= hi * 1.4: emojis.append("🟡 підвищений")
            else:               emojis.append("🔴 надлишок")
        hm_em[col_hm] = emojis
    df_em = pd.DataFrame(hm_em, index=[f"День {d}" for d in range(days+1)])
    st.caption("Статус кожного елемента по днях прогнозу:")
    st.dataframe(df_em, use_container_width=True)

# ======================== 14. ВАЛІДАЦІЯ ========================
with st.expander("🛡️ 14. Валідація та безпека"):
    st.markdown(f"""
| Параметр | Значення | Норма | Статус |
|----------|----------|-------|--------|
| NO3 | {final_no3:.1f} мг/л | 5–40 | {"✅" if 5 <= final_no3 <= 40 else "⚠️"} |
| PO4 | {final_po4:.2f} мг/л | 0.2–2.5 | {"✅" if 0.2 <= final_po4 <= 2.5 else "⚠️"} |
| CO₂ | {co2_val:.1f} мг/л | {co2_min_opt}–{co2_max_opt} | {"✅" if co2_min_opt <= co2_val <= co2_max_opt else "⚠️"} |
| K/GH | {k_gh_ratio:.2f} | 1.5–2.5 | {"✅" if 1.5 <= k_gh_ratio <= 2.5 else "⚠️"} |
    """)
    if final_no3 > 40:          st.error("🚨 NO3 > 40 — зменшіть N")
    if final_po4 > 2.5:         st.warning("⚠️ PO4 > 2.5 — ризик водоростей")
    if co2_val > co2_max_opt:   st.error("🚨 CO₂ надлишок — зменшіть подачу")
    if final_k > k_range['max']: st.warning("⚠️ K > максимуму — ризик блокування Ca/Mg")

st.caption("⚡ Toxicode V14 | Реальний баланс | Симулятор NO3/PO4/K | Інструкція ремінералізатора | Прогноз без суперечностей")
