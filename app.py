import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V9.2", layout="wide")
st.title("🌿 Toxicode Aquarium System V9.2 — Професійний гідрохімічний аналіз")

# ======================== HELPER FUNCTIONS ========================
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def get_ml_dose(curr, target, conc, vol):
    """Повертає мл добрива для досягнення target з curr"""
    return ((target - curr) * vol) / conc if curr < target else 0.0

def calculate_co2(kh, ph):
    """
    CO₂ (мг/л) = 3 * KH * 10^(7-pH)
    Для форсованих травників оптимальний діапазон 25-45 мг/л
    """
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
    """
    Повертає (мінімум, оптимум_низ, оптимум_верх, максимум) K в мг/л для заданого GH
    Формула: K_opt = GH × 1.8, діапазон ±30%
    """
    opt = gh * 1.8
    return {
        'min': gh * 1.2,
        'opt_low': gh * 1.5,
        'opt_high': gh * 2.5,
        'max': gh * 3.0,
        'target': opt
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
    custom_redfield = st.slider("Бажана пропорція Редфілда (N:1P)", 5, 30, 15)
    co2_min_opt = st.slider("Нижня межа CO₂ (мг/л)", 15, 35, 25, 
                            help="Для голландських травників рекомендується 25-30")
    co2_max_opt = st.slider("Верхня межа CO₂ (мг/л)", 30, 60, 45,
                            help="Для голландських травників до 45 мг/л безпечно")
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
            # Споживання = (початок*(1-підміна) + додано - зараз) / дні
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

# Розрахунок після підміни
after_no3 = no3_now * (1 - pct) + water_no3 * pct
after_po4 = po4_now * (1 - pct) + water_po4 * pct
after_k = k_now * (1 - pct) + water_k * pct
after_tds = base_tds * (1 - pct) + water_tds * pct

# ======================== 4. ДОЗУВАННЯ ДОБРИВ ========================
st.header("🧪 Дозування добрив")
st.caption("Концентрація готового розчину (г/л) та доза (мл/день)")

cd_n, cd_p, cd_k, cd_fe = st.columns(4)

with cd_n:
    conc_n = st.number_input("N (NO3) г/л", value=50.0, step=5.0, key="conc_n")
    dose_n_ml = st.number_input("Доза N мл/день", value=0.0, step=1.0, key="dose_n")
    add_no3 = (dose_n_ml * conc_n) / tank_vol

with cd_p:
    conc_p = st.number_input("P (PO4) г/л", value=5.0, step=0.5, key="conc_p")
    dose_p_ml = st.number_input("Доза P мл/день", value=0.0, step=0.5, key="dose_p")
    add_po4 = (dose_p_ml * conc_p) / tank_vol

with cd_k:
    conc_k = st.number_input("K г/л", value=20.0, step=2.0, key="conc_k")
    dose_k_ml = st.number_input("Доза K мл/день", value=0.0, step=1.0, key="dose_k")
    add_k = (dose_k_ml * conc_k) / tank_vol

with cd_fe:
    conc_fe = st.number_input("Fe г/л", value=1.0, step=0.1, key="conc_fe")
    dose_fe_ml = st.number_input("Доза Fe мл/день", value=0.0, step=0.5, key="dose_fe")
    add_fe = (dose_fe_ml * conc_fe) / tank_vol

# Фінальні значення після дозування
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
    curr_n = clamp(curr_n + (dose_n_ml * conc_n / tank_vol) - (daily_no3 * stability), 0, 100)
    curr_p = clamp(curr_p + (dose_p_ml * conc_p / tank_vol) - (daily_po4 * stability), 0, 10)
    curr_k = clamp(curr_k + (dose_k_ml * conc_k / tank_vol) - (daily_k * stability), 0, 100)

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)
# ======================== 7. K/GH РОЗШИРЕНИЙ АНАЛІЗ ========================
st.header("🧂 4. K/GH співвідношення — контроль антагонізму")

# Отримуємо оптимальні значення K для поточного GH
k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

# Показуємо формулу розрахунку
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

# Кольорова індикація
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
        st.write(f"K в межах норми {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f}")
    elif final_k <= k_opt_range['max']:
        st.warning(f"⚠️ **Початок антагонізму K**")
        st.write(f"Знизьте K на **{final_k - k_opt_range['opt_high']:.1f}** мг/л")
    else:
        st.error(f"🚨 **КРИТИЧНИЙ ПЕРЕДОЗИР K**")
        st.write(f"Терміново знизьте K на **{final_k - k_opt_range['max']:.1f}** мг/л")

# Діагностика за симптомами — ПОВНІ ВКЛАДКИ (як було)
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
        **Рішення при дефіциті K (поточний {final_k:.1f} → ціль {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f}):**
        
        - **Підніміть K на {k_opt_range['opt_low'] - final_k:.1f}–{k_opt_range['opt_high'] - final_k:.1f} мг/л**
        - Додавайте K поступово, не більше ніж +5 мг/л за день
        - Переконайтеся, що NO3 в нормі (зараз {final_no3:.1f} мг/л)
        - При одночасному дефіциті N використовуйте KNO₃-вмісне добриво
        """)
    elif final_k > k_opt_range['opt_high']:
        st.warning(f"""
        **Рішення при надлишку K (поточний {final_k:.1f} → ціль {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f}):**
        
        - **Знизьте K на {final_k - k_opt_range['opt_high']:.1f} мг/л**
        - Припиніть додавати K-вмісні добрива на 1-2 тижні
        - Зробіть підміну 30-50% води (разова або двічі по 25%)
        - Якщо використовуєте KNO₃ — замініть частину на NH₄NO₃-вмісне добриво
        - Додайте Ca/Mg (підвищте GH, якщо нижче {gh} °dH)
        """)
    else:
        st.success(f"""
        **K/GH в ідеальному балансі:**
        
        - Поточний K = {final_k:.1f} мг/л в діапазоні {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f}
        - Продовжуйте поточне дозування
        - Контролюйте K щотижня, особливо після великих підмін
        """)

with tab_chemistry:
    st.markdown(f"""
    ### ⚡ Механізм антагонізму K/Ca/Mg
    
    **Чому це важливо:**
    
    | Іон | Роль в рослині | Конкуренція |
    |-----|----------------|-------------|
    | **K⁺** | Активатор ферментів, осморегуляція | Займає канали швидко |
    | **Ca²⁺** | Структура стінок клітин, сигналізація | Витісняється K⁺ при надлишку |
    | **Mg²⁺** | Центральний атом хлорофілу | Блокується при K/Ca дисбалансі |
    
    **Як це працює:**
    
    1. K⁺, Ca²⁺, Mg²⁺ використовують спільні транспортні білки (іонні канали)
    2. При високій концентрації K⁺ (K/GH > 2.5) канали насичуються K⁺
    3. Ca²⁺ та Mg²⁺ не можуть потрапити в клітини → **функціональний дефіцит**
    4. Рослина "думає", що їй не вистачає Ca/Mg, навіть якщо GH в нормі
    
    **Ваші показники:**
    - GH = {gh} °dH
    - K = {final_k:.1f} мг/л
    - K/GH = {k_gh_ratio:.2f}
    - Статус: {"⚠️ Ризик антагонізму" if k_gh_ratio > 2.5 else "✅ Безпечно" if k_gh_ratio < 2.5 else "🔴 Критично"}
    
    **Формули запам'ятовування:**
    

# ======================== 8. ЕКСПЕРТНИЙ АНАЛІЗ ========================
st.header("📝 5. Гідрохімічний експертний висновок")

co2_val = calculate_co2(kh, ph)
redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)
f_end = forecast[-1]

col_adv, col_metrics = st.columns([1.5, 1])

with col_adv:
    st.subheader("💡 Аналіз та рекомендації")
    
    # CO2 (оновлений діапазон для форсованих травників)
    if co2_val < co2_min_opt:
        st.warning(f"💨 **Дефіцит CO₂ ({co2_val:.1f} мг/л):** Для голландського травника потрібно {co2_min_opt}–{co2_max_opt} мг/л. Збільште подачу.")
    elif co2_val > co2_max_opt:
        st.error(f"🐟 **Високий CO₂ ({co2_val:.1f} мг/л):** Ризик для риб при {co2_val} > {co2_max_opt}. Зменште подачу або посильте аерацію.")
    else:
        st.success(f"✅ CO₂ в нормі: {co2_val:.1f} мг/л (оптимум {co2_min_opt}–{co2_max_opt})")
    
    # Redfield баланс
    if redfield_status == "дефіцит N":
        needed_n_ml = ((final_po4 * custom_redfield - final_no3) * tank_vol) / conc_n if conc_n > 0 else 0
        st.error(f"⚠️ **Дефіцит азоту:** Додайте {needed_n_ml:.1f} мл N добрива для балансу N:P = {custom_redfield}:1")
    elif redfield_status == "дефіцит P":
        needed_p_ml = ((final_no3 / custom_redfield - final_po4) * tank_vol) / conc_p if conc_p > 0 else 0
        st.error(f"⚠️ **Дефіцит фосфору:** Додайте {needed_p_ml:.1f} мл P добрива")
    else:
        st.success(f"✅ Redfield баланс: {redfield_ratio:.1f}:1 (ціль {custom_redfield}:1)")
    
    # K/GH підсумок
    if final_k < k_opt_range['opt_low']:
        st.info(f"📈 **Потрібно підняти K:** з {final_k:.1f} до {k_opt_range['opt_low']:.0f} мг/л (+{k_opt_range['opt_low'] - final_k:.1f} мг/л)")
    elif final_k > k_opt_range['opt_high']:
        st.info(f"📉 **Потрібно знизити K:** з {final_k:.1f} до {k_opt_range['opt_high']:.0f} мг/л (-{final_k - k_opt_range['opt_high']:.1f} мг/л)")

with col_metrics:
    st.subheader("📊 Ключові метрики")
    st.metric("CO₂ (мг/л)", f"{co2_val:.1f}", delta=f"норма {co2_min_opt}-{co2_max_opt}")
    st.metric("Redfield (N:P)", f"{redfield_ratio:.1f}:1", delta=f"ціль {custom_redfield}:1")
    st.metric("K/GH", f"{k_gh_ratio:.2f}", delta=f"ціль {k_opt_range['target']/gh:.2f}")
    st.metric("TDS", f"{final_tds:.0f}", delta=f"{final_tds - target_tds:.0f} від цілі")

# ======================== 9. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.subheader("📅 6. План корекції на наступний період")

ml_n_needed = get_ml_dose(f_end["NO3"], target_no3, conc_n, tank_vol)
ml_p_needed = get_ml_dose(f_end["PO4"], target_po4, conc_p, tank_vol)
ml_k_needed = get_ml_dose(f_end["K"], target_k, conc_k, tank_vol)

col_rec1, col_rec2, col_rec3 = st.columns(3)
with col_rec1:
    st.metric("Додатково N", f"{ml_n_needed/days:.1f} мл/день", 
              delta=f"{ml_n_needed:.1f} мл за {days} днів")
with col_rec2:
    st.metric("Додатково P", f"{ml_p_needed/days:.2f} мл/день", 
              delta=f"{ml_p_needed:.1f} мл за {days} днів")
with col_rec3:
    st.metric("Додатково K", f"{ml_k_needed/days:.1f} мл/день", 
              delta=f"{ml_k_needed:.1f} мл за {days} днів")

# ======================== 10. ЗВІТ ДЛЯ КОПІЮВАННЯ ========================
st.divider()
st.subheader("📋 7. Звіт для журналу")

report = f"""=== TOXICODE AQUARIUM V9.2 REPORT ===
📅 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

【ОСНОВНІ ПАРАМЕТРИ】
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} °dH | KH: {kh} °dH | pH: {ph} | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л (норма {co2_min_opt}-{co2_max_opt})

【МАКРО】
NO3: {final_no3:.1f} / {target_no3} мг/л
PO4: {final_po4:.2f} / {target_po4} мг/л
K:   {final_k:.1f} / {target_k} мг/л

【БАЛАНСИ】
Redfield: {redfield_ratio:.1f}:1 (ціль {custom_redfield}:1) → {redfield_status}
K/GH: {k_gh_ratio:.2f} (норма 1.5-2.5, ціль {k_opt_range['target']/gh:.2f})
Оптимум K для GH={gh}: {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f} мг/л

【ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ】
NO3: {f_end['NO3']:.1f} → потрібно {ml_n_needed:.1f} мл N
PO4: {f_end['PO4']:.2f} → потрібно {ml_p_needed:.1f} мл P
K:   {f_end['K']:.1f}   → потрібно {ml_k_needed:.1f} мл K

【РЕКОМЕНДАЦІЯ ДОЗУВАННЯ (додатково до поточної дози)】
N: {ml_n_needed/days:.1f} мл/день
P: {ml_p_needed/days:.2f} мл/день
K: {ml_k_needed/days:.1f} мл/день

【K КОРЕКЦІЯ】
Поточний K: {final_k:.1f} мг/л
Цільовий діапазон: {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f} мг/л
Необхідна зміна: {"+" if final_k < k_opt_range['opt_low'] else "-"}{abs(k_opt_range['target'] - final_k):.1f} мг/л
====================================="""

st.code(report, language="text")

# ======================== 11. ВАЛІДАЦІЯ ТА БЕЗПЕКА ========================
with st.expander("🛡️ Валідація та безпека"):
    st.markdown(f"""
    | Перевірка | Поточне | Безпечний діапазон | Статус |
    |-----------|---------|--------------------|--------|
    | **NO3** | {final_no3:.1f} | 5–40 | {"✅" if 5 <= final_no3 <= 40 else "⚠️"} |
    | **PO4** | {final_po4:.2f} | 0.2–2.5 | {"✅" if 0.2 <= final_po4 <= 2.5 else "⚠️"} |
    | **CO₂** | {co2_val:.1f} | {co2_min_opt}–{co2_max_opt} | {"✅" if co2_min_opt <= co2_val <= co2_max_opt else "⚠️"} |
    | **K/GH** | {k_gh_ratio:.2f} | 1.5–2.5 | {"✅" if 1.5 <= k_gh_ratio <= 2.5 else "⚠️"} |
    | **TDS** | {final_tds:.0f} | {target_tds-50}–{target_tds+100} | {"✅" if target_tds-50 <= final_tds <= target_tds+100 else "⚠️"} |
    """)
    
    warnings = []
    if final_no3 > 40:
        warnings.append("🚨 Високий NO3 — зменште N добрива")
    if final_no3 < 3:
        warnings.append("⚠️ Низький NO3 — рослини голодують")
    if final_po4 > 2.5:
        warnings.append("⚠️ Високий PO4 — ризик водоростей")
    if co2_val > co2_max_opt:
        warnings.append("🚨 Зменште подачу CO₂")
    if co2_val < co2_min_opt:
        warnings.append("⚠️ Збільште подачу CO₂ для гарного росту")
    if final_k > k_opt_range['max']:
        warnings.append("⚠️ K вище максимуму — ризик блокування Ca/Mg")
    if final_k < k_opt_range['min']:
        warnings.append("⚠️ K нижче мінімуму — дефіцит")
    
    for w in warnings:
        st.warning(w)
    
    if not warnings:
        st.success("✅ Всі параметри в безпечних межах")

st.caption("⚡ Toxicode V9.2 | Для просунутих акваріумістів | Формула: K_opt = GH × 1.8")
