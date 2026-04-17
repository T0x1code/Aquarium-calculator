import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V9.3", layout="wide")
st.title("🌿 Toxicode Aquarium System V9.5 — C:N:P:K + Повний контроль")

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
    """Повертає (мінімум, оптимум_низ, оптимум_верх, максимум) K в мг/л для заданого GH"""
    return {
        'min': gh * 1.2,
        'opt_low': gh * 1.5,
        'opt_high': gh * 2.5,
        'max': gh * 3.0,
        'target': gh * 1.8
    }

def calculate_cnpk_status(carbon_estimate, no3, po4, k):
    """
    Оцінка співвідношення C:N:P:K
    Повертає словник зі статусами та рекомендаціями
    """
    # Цільові співвідношення (молярні) для водних рослин
    # C:N:P:K ≈ 500:30:1:15 (масове співвідношення приблизне)
    # Переводимо в масове для зручності
    
    # Якщо є оцінка вуглецю (з CO₂)
    if carbon_estimate > 0:
        c_ratio = carbon_estimate / po4 if po4 > 0 else 999
        c_status = "норма" if 200 < c_ratio < 600 else "дефіцит C" if c_ratio <= 200 else "надлишок C"
    else:
        c_status = "невідомо (потрібен тест CO₂)"
    
    # N:P
    np_ratio = no3 / po4 if po4 > 0 else 999
    if np_ratio < 10:
        np_status = "дефіцит N"
    elif np_ratio > 22:
        np_status = "дефіцит P"
    else:
        np_status = "баланс"
    
    # K відносно N (K:N масове ≈ 0.5-1.0)
    kn_ratio = k / no3 if no3 > 0 else 999
    if kn_ratio < 0.3:
        k_status = "дефіцит K"
    elif kn_ratio > 1.5:
        k_status = "надлишок K"
    else:
        k_status = "баланс"
    
    return {
        'c_status': c_status,
        'np_ratio': np_ratio,
        'np_status': np_status,
        'kn_ratio': kn_ratio,
        'k_status': k_status,
        'recommendations': []
    }

def calculate_steady_state(daily_dose, weekly_change_pct):
    """Розрахунок накопичення: де зупиниться концентрація через місяці"""
    if weekly_change_pct <= 0: return daily_dose * 365 
    return (daily_dose * 7) / weekly_change_pct

def get_liebig_metrics(co2, no3, po4, k, fe, targets):
    """Нормалізація для графіка Лібіха (0.0 - 1.5)"""
    return {
        "C (CO2)": min(co2 / 30.0, 1.5),
        "N (NO3)": min(no3 / targets['no3'], 1.5) if targets['no3'] > 0 else 0,
        "P (PO4)": min(po4 / targets['po4'], 1.5) if targets['po4'] > 0 else 0,
        "K": min(k / targets['k'], 1.5) if targets['k'] > 0 else 0,
        "Fe": min(fe / targets['fe'], 1.5) if targets['fe'] > 0 else 0
    }

# ======================== SIDEBAR — ГЛОБАЛЬНА КОНФІГУРАЦІЯ ========================
with st.sidebar:
    st.header("📏 Конфігурація системи")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)
    
    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0, step=0.1)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0, step=1.0)
    target_tds = st.number_input("Ціль TDS", value=120.0, step=5.0)
    
    st.divider()
    st.subheader("⚙️ Розширені налаштування")
    custom_redfield = st.slider("Бажана пропорція Редфілда (N:P)", 5, 30, 15)
    
    # CO₂ слайдери — тепер 0-100
    co2_min_opt = st.slider("Нижня межа CO₂ (мг/л)", 0, 100, 25)
    co2_max_opt = st.slider("Верхня межа CO₂ (мг/л)", 0, 100, 45)
    
    days = st.slider("Період прогнозу (днів)", 1, 14, 7)

# ======================== 1. КАЛЬКУЛЯТОР РЕАЛЬНОГО СПОЖИВАННЯ ========================
st.header("📉 1. Калькулятор реального споживання (на основі тестів)")
consumption_results = {}

with st.expander("Аналіз минулого періоду — введіть дані двох тестів"):
    t1, t2, t3 = st.tabs(["Азот (NO3)", "Фосфор (PO4)", "Калій (K)"])
    
    def calc_real_cons(tab, name, key_p):
        with tab:
            c1, c2, c3 = st.columns(3)
            p_test = c1.number_input(f"Тест {name} (початок періоду)", value=15.0, step=0.1, key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=10.0, step=0.1, key=f"c_{key_p}")
            added = c3.number_input(f"Внесено {name} за період (мг/л)", value=0.0, step=0.1, key=f"a_{key_p}")
            
            cl1, cl2 = st.columns(2)
            ch_l = cl1.number_input(f"Літрів підмінено за період ({name})", value=0.0, step=1.0, key=f"ch_l_{key_p}")
            days_between = cl2.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key_p}")
            
            pct_water_change = (ch_l / tank_vol) if tank_vol > 0 else 0
            res = (p_test * (1 - pct_water_change) + added - c_test) / days_between
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"**Щоденне споживання {name}:** {val:.2f} мг/л в день")
    
    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

# ======================== 2. ПОТОЧНИЙ СТАН ========================
st.header("📋 2. Поточні параметри води")
col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("NO3 (мг/л)", value=10.0, step=1.0)
    po4_now = st.number_input("PO4 (мг/л)", value=0.5, step=0.1)
    k_now = st.number_input("K (мг/л)", value=10.0, step=1.0)
    base_tds = st.number_input("TDS", value=150.0, step=5.0)

with col2:
    gh = st.number_input("GH (°dH)", value=6, step=1, 
                         help="1°dH = 7.14 мг/л CaO або 10 мг/л CaO")
    kh = st.number_input("KH (°dH)", value=2, step=1)
    ph = st.number_input("pH", value=6.8, step=0.1)

with col3:
    default_no3_cons = consumption_results.get('NO3', 2.0)
    default_po4_cons = consumption_results.get('PO4', 0.1)
    default_k_cons = consumption_results.get('K', 1.0)
    
    daily_no3 = st.number_input("Споживання NO3 (мг/л/день)", value=default_no3_cons, step=0.1)
    daily_po4 = st.number_input("Споживання PO4 (мг/л/день)", value=default_po4_cons, step=0.1)
    daily_k = st.number_input("Споживання K (мг/л/день)", value=default_k_cons, step=0.1)

# ======================== 3. ПІДМІНА ВОДИ ========================
st.divider()
st.header("💧 Підміна води")
c_change, c_quality = st.columns(2)

with c_change:
    change_l = st.number_input("Літри підміни", value=50.0, step=1.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.metric("Відсоток підміни", f"{pct*100:.1f}%")

with c_quality:
    water_no3 = st.number_input("NO3 у новій воді (мг/л)", value=0.0, step=0.5)
    water_po4 = st.number_input("PO4 у новій воді (мг/л)", value=0.0, step=0.1)
    water_k = st.number_input("K у новій воді (мг/л)", value=0.0, step=1.0)
    water_tds = st.number_input("TDS нової води", value=110.0, step=5.0)

after_no3 = no3_now * (1 - pct) + water_no3 * pct
after_po4 = po4_now * (1 - pct) + water_po4 * pct
after_k = k_now * (1 - pct) + water_k * pct
after_tds = base_tds * (1 - pct) + water_tds * pct

# ======================== 4. ДОЗУВАННЯ ДОБРИВ ========================
st.header("🧪 Дозування добрив")
st.caption("Концентрація готового розчину (г/л) та поточна доза (мл/день)")

cd_n, cd_p, cd_k, cd_fe = st.columns(4)

with cd_n:
    conc_n = st.number_input("N (NO3) г/л", value=50.0, step=5.0, key="conc_n")
    current_dose_n_ml = st.number_input("Поточна доза N мл/день", value=0.0, step=1.0, key="dose_n")
    add_no3 = (current_dose_n_ml * conc_n) / tank_vol

with cd_p:
    conc_p = st.number_input("P (PO4) г/л", value=5.0, step=0.5, key="conc_p")
    current_dose_p_ml = st.number_input("Поточна доза P мл/день", value=0.0, step=0.5, key="dose_p")
    add_po4 = (current_dose_p_ml * conc_p) / tank_vol

with cd_k:
    conc_k = st.number_input("K г/л", value=20.0, step=2.0, key="conc_k")
    current_dose_k_ml = st.number_input("Поточна доза K мл/день", value=0.0, step=1.0, key="dose_k")
    add_k = (current_dose_k_ml * conc_k) / tank_vol

with cd_fe:
    conc_fe = st.number_input("Fe г/л", value=1.0, step=0.1, key="conc_fe")
    current_dose_fe_ml = st.number_input("Поточна доза Fe мл/день", value=0.0, step=0.5, key="dose_fe")
    add_fe = (current_dose_fe_ml * conc_fe) / tank_vol

final_no3 = after_no3 + add_no3
final_po4 = after_po4 + add_po4
final_k = after_k + add_k
final_tds = after_tds + (add_no3 + add_po4 + add_k + add_fe) * 0.5

# ======================== 5. СТАБІЛЬНІСТЬ ТА АДАПТАЦІЯ ========================
ratio_now = final_no3 / final_po4 if final_po4 > 0 else 0
stability = 1 / (1 + abs((ratio_now - custom_redfield) / custom_redfield))
st.caption(f"🎚️ **Коефіцієнт стабільності (Redfield):** {stability:.2f} — впливає на прогноз споживання")

# ======================== 6. ПРОГНОЗ НА days ДНІВ ========================
st.header(f"📈 3. Динамічний прогноз на {days} днів")

forecast = []
curr_n, curr_p, curr_k = final_no3, final_po4, final_k

for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": round(curr_n, 1),
        "PO4": round(curr_p, 2),
        "K": round(curr_k, 1)
    })
    curr_n = clamp(curr_n + (current_dose_n_ml * conc_n / tank_vol) - (daily_no3 * stability), 0, 100)
    curr_p = clamp(curr_p + (current_dose_p_ml * conc_p / tank_vol) - (daily_po4 * stability), 0, 10)
    curr_k = clamp(curr_k + (current_dose_k_ml * conc_k / tank_vol) - (daily_k * stability), 0, 100)

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)

# ======================== 7. C:N:P:K АНАЛІЗ (НОВИЙ БЛОК) ========================
st.header("⚖️ 4. C:N:P:K співвідношення — повний баланс")
st.caption("Для здорових рослин потрібен баланс всіх чотирьох елементів: Вуглець, Азот, Фосфор, Калій")

co2_val = calculate_co2(kh, ph)
cnpk_status = calculate_cnpk_status(co2_val, final_no3, final_po4, final_k)

col_c, col_n, col_p, col_k_bal = st.columns(4)

with col_c:
    st.metric("CO₂ (C)", f"{co2_val:.1f} мг/л", 
              delta="C джерело", delta_color="off")
    if co2_val < co2_min_opt:
        st.caption("🔴 Дефіцит C")
    elif co2_val > co2_max_opt:
        st.caption("🟡 Надлишок C")
    else:
        st.caption("✅ C норма")

with col_n:
    st.metric("NO₃ (N)", f"{final_no3:.1f} мг/л")
    if cnpk_status['np_status'] == "дефіцит N":
        st.caption("🔴 Дефіцит N")
    elif cnpk_status['np_status'] == "дефіцит P":
        st.caption("🟡 Баланс N:P")
    else:
        st.caption("✅ N норма")

with col_p:
    st.metric("PO₄ (P)", f"{final_po4:.2f} мг/л")
    if cnpk_status['np_status'] == "дефіцит P":
        st.caption("🔴 Дефіцит P")
    else:
        st.caption("✅ P норма" if final_po4 > 0.2 else "⚠️ Низький P")

with col_k_bal:
    st.metric("K", f"{final_k:.1f} мг/л")
    if cnpk_status['k_status'] == "дефіцит K":
        st.caption("🔴 Дефіцит K")
    elif cnpk_status['k_status'] == "надлишок K":
        st.caption("🟡 Надлишок K")
    else:
        st.caption("✅ K норма")

# Розширений аналіз C:N:P:K
with st.expander("📊 Детальний аналіз C:N:P:K співвідношень"):
    st.markdown(f"""
    ### Поточні співвідношення
    
    | Співвідношення | Поточне | Оптимальне | Статус |
    |----------------|---------|------------|--------|
    | **N:P** | {cnpk_status['np_ratio']:.1f}:1 | 15:1 | {cnpk_status['np_status']} |
    | **K:N** | {cnpk_status['kn_ratio']:.2f}:1 | 0.5–1.0:1 | {cnpk_status['k_status']} |
    | **C:N** (оцінка) | {(co2_val/final_no3) if final_no3 > 0 else 0:.1f}:1 | 30–50:1 | залежить від CO₂ |
    | **C:P** (оцінка) | {(co2_val/final_po4) if final_po4 > 0 else 0:.1f}:1 | 300–500:1 | залежить від CO₂ |
    
    ### 📖 Довідка: оптимальні масові співвідношення для водних рослин
    
    | Елементи | Співвідношення (масове) | Пояснення |
    |----------|------------------------|-----------|
    | **C : N** | 30–50 : 1 | Вуглець з CO₂, азот з NO₃ |
    | **N : P** | 10–22 : 1 | Класичний Redfield (15:1 ідеал) |
    | **K : N** | 0.5–1.0 : 1 | Калій має бути пропорційний азоту |
    | **C : P** | 300–500 : 1 | Похідне від C:N + N:P |
    
    ### ⚠️ Що порушено?
    """)
    
    recommendations = []
    
    # CO₂ перевірка
    if co2_val < co2_min_opt:
        recommendations.append(f"🔴 **Дефіцит вуглецю (C):** CO₂ = {co2_val:.1f} мг/л (норма {co2_min_opt}–{co2_max_opt}). Збільште подачу CO₂.")
    elif co2_val > co2_max_opt:
        recommendations.append(f"🟡 **Надлишок вуглецю (C):** CO₂ = {co2_val:.1f} мг/л. Можливий ризик для риб при тривалому перевищенні.")
    else:
        recommendations.append(f"✅ CO₂ в нормі: {co2_val:.1f} мг/л")
    
    # N:P перевірка
    if cnpk_status['np_status'] == "дефіцит N":
        recommendations.append(f"🔴 **Дефіцит азоту (N):** N:P = {cnpk_status['np_ratio']:.1f}:1 (ціль 15:1). Збільште дозу N добрива.")
    elif cnpk_status['np_status'] == "дефіцит P":
        recommendations.append(f"🔴 **Дефіцит фосфору (P):** N:P = {cnpk_status['np_ratio']:.1f}:1 (ціль 15:1). Збільште дозу P добрива.")
    else:
        recommendations.append(f"✅ N:P баланс: {cnpk_status['np_ratio']:.1f}:1")
    
    # K перевірка
    if cnpk_status['k_status'] == "дефіцит K":
        recommendations.append(f"🔴 **Дефіцит калію (K):** K:N = {cnpk_status['kn_ratio']:.2f}:1 (норма 0.5–1.0). Збільште дозу K добрива.")
    elif cnpk_status['k_status'] == "надлишок K":
        recommendations.append(f"🟡 **Надлишок калію (K):** K:N = {cnpk_status['kn_ratio']:.2f}:1 > 1.5. Зменште дозу K добрива.")
    else:
        recommendations.append(f"✅ K:N баланс: {cnpk_status['kn_ratio']:.2f}:1")
    
    for rec in recommendations:
        st.write(rec)

# ======================== 8. K/GH АНАЛІЗ ========================
st.header("🧂 5. K/GH співвідношення — контроль антагонізму")

k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("📐 Як розрахувати цільовий K за GH", expanded=True):
    st.markdown(f"""
    ### Формула оптимального калію
    
    **Для вашого GH = {gh} °dH:**
    
    | Показник | Формула | Значення (мг/л K) |
    |----------|---------|-------------------|
    | Мінімум | GH × 1.2 | **{k_opt_range['min']:.1f}** |
    | Оптимум (нижня межа) | GH × 1.5 | **{k_opt_range['opt_low']:.1f}** |
    | Оптимум (ціль) | GH × 1.8 | **{k_opt_range['target']:.1f}** |
    | Оптимум (верхня межа) | GH × 2.5 | **{k_opt_range['opt_high']:.1f}** |
    | Максимум | GH × 3.0 | **{k_opt_range['max']:.1f}** |
    
    > **Запам'ятайте:** `K_ціль (мг/л) = GH × 1.8`
    > 
    > Допустимий діапазон: `GH × 1.5` до `GH × 2.5`
    """)

col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Поточний K", f"{final_k:.1f} мг/л")
    st.caption(f"GH = {gh} °dH")

with col_k2:
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}", 
              delta=f"ціль {k_opt_range['target']/gh:.2f}", 
              delta_color="off")

with col_k3:
    if final_k < k_opt_range['min']:
        st.error(f"🚨 **КРИТИЧНИЙ ДЕФІЦИТ K**")
        st.write(f"Потрібно підняти на **{k_opt_range['min'] - final_k:.1f}** мг/л")
    elif final_k < k_opt_range['opt_low']:
        st.warning(f"⚠️ **Помірний дефіцит K**")
        st.write(f"Підніміть до **{k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f}** мг/л")
    elif final_k <= k_opt_range['opt_high']:
        st.success(f"✅ **Оптимальний K**")
    elif final_k <= k_opt_range['max']:
        st.warning(f"⚠️ **Початок антагонізму K**")
        st.write(f"Знизьте K на **{final_k - k_opt_range['opt_high']:.1f}** мг/л")
    else:
        st.error(f"🚨 **КРИТИЧНИЙ ПЕРЕДОЗИР K**")
        st.write(f"Терміново знизьте K на **{final_k - k_opt_range['max']:.1f}** мг/л")

# Діагностика за симптомами
st.subheader("🌿 Діагностика за симптомами")
tab_symptoms, tab_solutions, tab_chemistry = st.tabs(["Симптоми на рослинах", "Рішення", "Хімічний механізм"])

with tab_symptoms:
    st.markdown("""
    | Стан | Старе листя | Молоде листя | Корені |
    |------|-------------|--------------|--------|
    | **Дефіцит K** | Жовті/бурі краї, дірки | Дрібне, світле | Слабкі, тонкі |
    | **Надлишок K** | Темно-зелене, товсте | Скручене, білі кінчики | "Радікуліт" (гниль кінчиків) |
    | **Антагонізм K/Ca** | Норма | Деформоване, відмираючі точки росту | Короткі, товсті |
    
    ### Як відрізнити дефіцит K від дефіциту N?
    | Ознака | Дефіцит K | Дефіцит N |
    |--------|-----------|-----------|
    | Локалізація | Краї та кінчики листя | Все листя рівномірно |
    | Колір | Жовто-коричневий | Світло-зелений/жовтий |
    | Прожилки | Залишаються зеленими | Жовтіють разом з листям |
    """)

with tab_solutions:
    if final_k < k_opt_range['opt_low']:
        st.info(f"""
        **Рішення при дефіциті K:**
        
        - **Підніміть K на {k_opt_range['opt_low'] - final_k:.1f}–{k_opt_range['opt_high'] - final_k:.1f} мг/л**
        - Додавайте K поступово, не більше ніж +5 мг/л за день
        - Переконайтеся, що NO3 в нормі (зараз {final_no3:.1f} мг/л)
        """)
    elif final_k > k_opt_range['opt_high']:
        st.warning(f"""
        **Рішення при надлишку K:**
        
        - **Знизьте K на {final_k - k_opt_range['opt_high']:.1f} мг/л**
        - Припиніть додавати K-вмісні добрива на 1-2 тижні
        - Зробіть підміну 30-50% води
        """)
    else:
        st.success(f"✅ K/GH в ідеальному балансі. Продовжуйте поточне дозування.")

with tab_chemistry:
    st.markdown(f"""
    ### ⚡ Механізм антагонізму K/Ca/Mg
    
    **Ваші показники:**
    - GH = {gh} °dH
    - K = {final_k:.1f} мг/л
    - K/GH = {k_gh_ratio:.2f}
    - Статус: {"⚠️ Ризик антагонізму" if k_gh_ratio > 2.5 else "✅ Безпечно" if k_gh_ratio <= 2.5 else "🔴 Критично"}
    
    **Формули запам'ятовування:**
    """)

# ======================== 9. ПЛАН КОРЕКЦІЇ (ВИПРАВЛЕНО) ========================
st.divider()
st.header("📅 6. План корекції дозування")

f_end = forecast[-1]

# Розраховуємо необхідну зміну КОНЦЕНТРАЦІЇ в мг/л після days днів
delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4 - f_end["PO4"]
delta_k = target_k - f_end["K"]

# ВАЖЛИВО: розподіляємо зміну на days днів (це ДОБОВА зміна дози)
if delta_no3 > 0:
    # Скільки мг/л потрібно додавати КОЖНОГО ДНЯ
    daily_delta_no3 = delta_no3 / days
    change_n_ml = (daily_delta_no3 * tank_vol) / conc_n if conc_n > 0 else 0
    new_dose_n = current_dose_n_ml + change_n_ml
    correction_text_n = f"+{change_n_ml:.1f} мл/день"
elif delta_no3 < 0:
    daily_delta_no3 = abs(delta_no3) / days
    reduce_n_ml = (daily_delta_no3 * tank_vol) / conc_n if conc_n > 0 else 0
    new_dose_n = max(0, current_dose_n_ml - reduce_n_ml)
    correction_text_n = f"-{reduce_n_ml:.1f} мл/день"
else:
    new_dose_n = current_dose_n_ml
    correction_text_n = "без змін"

if delta_po4 > 0:
    daily_delta_po4 = delta_po4 / days
    change_p_ml = (daily_delta_po4 * tank_vol) / conc_p if conc_p > 0 else 0
    new_dose_p = current_dose_p_ml + change_p_ml
    correction_text_p = f"+{change_p_ml:.2f} мл/день"
elif delta_po4 < 0:
    daily_delta_po4 = abs(delta_po4) / days
    reduce_p_ml = (daily_delta_po4 * tank_vol) / conc_p if conc_p > 0 else 0
    new_dose_p = max(0, current_dose_p_ml - reduce_p_ml)
    correction_text_p = f"-{reduce_p_ml:.2f} мл/день"
else:
    new_dose_p = current_dose_p_ml
    correction_text_p = "без змін"

if delta_k > 0:
    daily_delta_k = delta_k / days
    change_k_ml = (daily_delta_k * tank_vol) / conc_k if conc_k > 0 else 0
    new_dose_k = current_dose_k_ml + change_k_ml
    correction_text_k = f"+{change_k_ml:.1f} мл/день"
elif delta_k < 0:
    daily_delta_k = abs(delta_k) / days
    reduce_k_ml = (daily_delta_k * tank_vol) / conc_k if conc_k > 0 else 0
    new_dose_k = max(0, current_dose_k_ml - reduce_k_ml)
    correction_text_k = f"-{reduce_k_ml:.1f} мл/день"
else:
    new_dose_k = current_dose_k_ml
    correction_text_k = "без змін"

col_rec1, col_rec2, col_rec3 = st.columns(3)

with col_rec1:
    st.subheader("🧪 Азот (N)")
    st.metric("Поточна доза", f"{current_dose_n_ml:.1f} мл/день")
    
    if delta_no3 > 0:
        st.warning(f"📈 **Дефіцит NO₃:** {delta_no3:.1f} мг/л за {days} днів")
        st.info(f"➕ **Додайте {change_n_ml:.1f} мл/день до поточної дози**")
    elif delta_no3 < 0:
        st.warning(f"📉 **Надлишок NO₃:** {abs(delta_no3):.1f} мг/л за {days} днів")
        st.info(f"➖ **Зменште на {reduce_n_ml:.1f} мл/день**")
    else:
        st.success("✅ NO₃ в нормі")
    
    st.metric("Нова рекомендована доза", f"{new_dose_n:.1f} мл/день")

with col_rec2:
    st.subheader("💧 Фосфор (P)")
    st.metric("Поточна доза", f"{current_dose_p_ml:.2f} мл/день")
    
    if delta_po4 > 0:
        st.warning(f"📈 **Дефіцит PO₄:** {delta_po4:.2f} мг/л за {days} днів")
        st.info(f"➕ **Додайте {change_p_ml:.2f} мл/день до поточної дози**")
    elif delta_po4 < 0:
        st.warning(f"📉 **Надлишок PO₄:** {abs(delta_po4):.2f} мг/л за {days} днів")
        st.info(f"➖ **Зменште на {reduce_p_ml:.2f} мл/день**")
    else:
        st.success("✅ PO₄ в нормі")
    
    st.metric("Нова рекомендована доза", f"{new_dose_p:.2f} мл/день")

with col_rec3:
    st.subheader("🌾 Калій (K)")
    st.metric("Поточна доза", f"{current_dose_k_ml:.1f} мл/день")
    
    if delta_k > 0:
        st.warning(f"📈 **Дефіцит K:** {delta_k:.1f} мг/л за {days} днів")
        st.info(f"➕ **Додайте {change_k_ml:.1f} мл/день до поточної дози**")
    elif delta_k < 0:
        st.warning(f"📉 **Надлишок K:** {abs(delta_k):.1f} мг/л за {days} днів")
        st.info(f"➖ **Зменште на {reduce_k_ml:.1f} мл/день**")
    else:
        st.success("✅ K в нормі")
    
    st.metric("Нова рекомендована доза", f"{new_dose_k:.1f} мл/день")

# Додаткова інформація
st.caption(f"""
💡 **Як читати рекомендації:**
- Дефіцит/надлишок вказано за **{days} днів**
- Корекція розподілена на **{days} днів** — це **ДОБОВА зміна** дози
- Приклад: якщо дефіцит 10 мг/л за 5 днів → додавайте +2 мг/л кожен день
- Змінюйте дозування **поступово**, не більше ніж на 20% за день
""")

# ======================== 10. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("📝 7. Експертний висновок")

co2_val = calculate_co2(kh, ph)
redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
    st.subheader("📊 Стан системи")
    
    # CO₂
    if co2_val < co2_min_opt:
        st.warning(f"💨 CO₂: {co2_val:.1f} мг/л — **дефіцит** (норма {co2_min_opt}–{co2_max_opt})")
    elif co2_val > co2_max_opt:
        st.error(f"🐟 CO₂: {co2_val:.1f} мг/л — **надлишок** (норма {co2_min_opt}–{co2_max_opt})")
    else:
        st.success(f"✅ CO₂: {co2_val:.1f} мг/л — норма")
    
    # Redfield
    if redfield_status == "дефіцит N":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — **дефіцит азоту** (ціль {custom_redfield}:1)")
    elif redfield_status == "дефіцит P":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — **дефіцит фосфору** (ціль {custom_redfield}:1)")
    else:
        st.success(f"✅ N:P = {redfield_ratio:.1f}:1 — баланс")
    
    # K/GH
    if final_k < k_opt_range['opt_low']:
        st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — **дефіцит K**")
    elif final_k > k_opt_range['opt_high']:
        st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — **надлишок K**")
    else:
        st.success(f"✅ K/GH = {k_gh_ratio:.2f} — норма")

with col_summary2:
    st.subheader(f"📋 Прогноз через {days} днів")
    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л", delta=f"{f_end['NO3'] - target_no3:.1f}")
    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л", delta=f"{f_end['PO4'] - target_po4:.2f}")
    st.metric("K", f"{f_end['K']:.1f} мг/л", delta=f"{f_end['K'] - target_k:.1f}")

# ======================== 11. ЗВІТ ДЛЯ КОПІЮВАННЯ ========================
st.divider()
st.subheader("📋 8. Звіт для журналу")

report = f"""=== TOXICODE AQUARIUM V9.3 REPORT ===
📅 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

【ОСНОВНІ ПАРАМЕТРИ】
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} °dH | KH: {kh} °dH | pH: {ph} | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л (норма {co2_min_opt}–{co2_max_opt})

【МАКРО】
NO3: {final_no3:.1f} / {target_no3} мг/л
PO4: {final_po4:.2f} / {target_po4} мг/л
K:   {final_k:.1f} / {target_k} мг/л

【C:N:P:K СПІВВІДНОШЕННЯ】
N:P = {cnpk_status['np_ratio']:.1f}:1 → {cnpk_status['np_status']}
K:N = {cnpk_status['kn_ratio']:.2f}:1 → {cnpk_status['k_status']}

【K/GH】
K/GH = {k_gh_ratio:.2f} (норма 1.5-2.5)
Оптимум K для GH={gh}: {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f} мг/л

【ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ】
NO3: {f_end['NO3']:.1f} мг/л
PO4: {f_end['PO4']:.2f} мг/л
K:   {f_end['K']:.1f} мг/л

【РЕКОМЕНДАЦІЯ ЗМІНИ ДОЗИ】
N: {current_dose_n_ml:.1f} → {max(0, new_dose_n):.1f} мл/день ({'+' if new_dose_n > current_dose_n_ml else ''}{new_dose_n - current_dose_n_ml:.1f})
P: {current_dose_p_ml:.2f} → {max(0, new_dose_p):.2f} мл/день ({'+' if new_dose_p > current_dose_p_ml else ''}{new_dose_p - current_dose_p_ml:.2f})
K: {current_dose_k_ml:.1f} → {max(0, new_dose_k):.1f} мл/день ({'+' if new_dose_k > current_dose_k_ml else ''}{new_dose_k - current_dose_k_ml:.1f})
====================================="""

st.code(report, language="text")

# ======================== 12. ВАЛІДАЦІЯ ========================
with st.expander("🛡️ Валідація та безпека"):
    st.markdown(f"""
    | Перевірка | Поточне | Безпечний діапазон | Статус |
    |-----------|---------|--------------------|--------|
    | **NO3** | {final_no3:.1f} | 5–40 | {"✅" if 5 <= final_no3 <= 40 else "⚠️"} |
    | **PO4** | {final_po4:.2f} | 0.2–2.5 | {"✅" if 0.2 <= final_po4 <= 2.5 else "⚠️"} |
    | **CO₂** | {co2_val:.1f} | {co2_min_opt}–{co2_max_opt} | {"✅" if co2_min_opt <= co2_val <= co2_max_opt else "⚠️"} |
    | **K/GH** | {k_gh_ratio:.2f} | 1.5–2.5 | {"✅" if 1.5 <= k_gh_ratio <= 2.5 else "⚠️"} |
    """)

    if final_no3 > 40:
        st.error("🚨 Високий NO3 — зменште N добрива")
    if final_po4 > 2.5:
        st.warning("⚠️ Високий PO4 — ризик водоростей")
    if co2_val > co2_max_opt:
        st.error("🚨 Зменште подачу CO₂")
    if final_k > k_opt_range['max']:
        st.warning("⚠️ K вище максимуму — ризик блокування Ca/Mg")

st.caption("⚡ Toxicode V9.3 | Повний контроль C:N:P:K | Динамічна корекція доз")
