import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V9.1", layout="wide")
st.title("🌿 Toxicode Aquarium System V9.1 — K/GH Контроль + Розумне дозування")

# ======================== HELPER FUNCTIONS ========================
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def get_ml_dose(curr, target, conc, vol):
    """Повертає мл добрива для досягнення target з curr"""
    return ((target - curr) * vol) / conc if curr < target else 0.0

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

def recommend_k_fertilizer(k_current, k_target, need_n, no3_current, no3_target):
    """
    Рекомендує яке добриво використовувати для корекції K
    Повертає (назва, кількість_мг_на_літр, пояснення)
    """
    k_need = k_target - k_current
    
    if k_need <= 0:
        return None, 0, "K вже в нормі, додавати не потрібно"
    
    # Якщо потрібен N і K — використовуємо KNO₃
    if need_n and no3_current < no3_target:
        # KNO₃ дає 1 мг K на 1.5 мг NO₃ (масове співвідношення)
        k_from_kno3 = k_need
        no3_from_kno3 = k_need * 1.5
        return "KNO₃", k_need, f"Дасть +{k_need:.1f} мг/л K та +{no3_from_kno3:.1f} мг/л NO₃"
    
    # Якщо N в нормі або надлишок — використовуємо K₂SO₄
    else:
        return "K₂SO₄", k_need, f"Дасть +{k_need:.1f} мг/л K без впливу на N/P"

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
    co2_limit = st.slider("Поріг тривоги CO2 (мг/л)", 20, 100, 35)
    days = st.slider("Період прогнозу (днів)", 1, 14, 7)

# ======================== 1. КАЛЬКУЛЯТОР РЕАЛЬНОГО СПОЖИВАННЯ ========================
st.header("📉 1. Калькулятор реального споживання (на основі тестів)")
consumption_results = {}

with st.expander("Аналіз минулого періоду"):
    t1, t2, t3 = st.tabs(["Азот (NO3)", "Фосфор (PO4)", "Калій (K)"])
    
    def calc_real_cons(tab, name, key_p):
        with tab:
            c1, c2, c3 = st.columns(3)
            p_test = c1.number_input(f"Тест {name} (початок)", value=15.0, step=0.1, key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=10.0, step=0.1, key=f"c_{key_p}")
            added = c3.number_input(f"Внесено {name} (мг/л)", value=0.0, step=0.1, key=f"a_{key_p}")
            
            cl1, cl2 = st.columns(2)
            ch_l = cl1.number_input(f"Літрів підмінено ({name})", value=0.0, step=1.0, key=f"ch_l_{key_p}")
            days_between = cl2.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key_p}")
            
            pct_water_change = (ch_l / tank_vol) if tank_vol > 0 else 0
            # Споживання = (початок*(1-підміна) + додано - зараз) / дні
            res = (p_test * (1 - pct_water_change) + added - c_test) / days_between
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"**Споживання {name}:** {val:.2f} мг/л в день")
    
    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

# ======================== 2. ПОТОЧНИЙ СТАН (ВСІ ПАРАМЕТРИ) ========================
st.header("📋 2. Поточні параметри води")
col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("Поточний NO3 (мг/л)", value=10.0, step=1.0)
    po4_now = st.number_input("Поточний PO4 (мг/л)", value=0.5, step=0.1)
    k_now = st.number_input("Поточний K (мг/л)", value=10.0, step=1.0)
    base_tds = st.number_input("Поточний TDS", value=150.0, step=5.0)

with col2:
    gh = st.number_input("GH (Загальна жорсткість, °dH)", value=6, step=1, 
                         help="1°dH = 7.14 мг/л CaO або 10 мг/л CaO")
    kh = st.number_input("KH (Карбонатна жорсткість, °dH)", value=2, step=1)
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
    water_tds = st.number_input("TDS нової води (після ремінералізації)", value=110.0, step=5.0)

# Розрахунок після підміни
after_no3 = no3_now * (1 - pct) + water_no3 * pct
after_po4 = po4_now * (1 - pct) + water_po4 * pct
after_k = k_now * (1 - pct) + water_k * pct
after_tds = base_tds * (1 - pct) + water_tds * pct

# ======================== 4. ДОЗУВАННЯ ДОБРИВ ========================
st.header("🧪 Дозування добрив")
st.caption("Концентрація розчину (г/л) та доза (мл/день)")

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

# ======================== 7. K/GH РОЗШИРЕНИЙ АНАЛІЗ (ГОЛОВНИЙ БЛОК) ========================
st.header("🧂 4. K/GH співвідношення — антагонізм калію з кальцієм/магнієм")

# Розрахунок норм для поточного GH
k_gh_ratio = final_k / gh if gh > 0 else 0
k_min = gh * 1.2
k_opt_low = gh * 1.5
k_opt_high = gh * 2.5
k_max = gh * 3.0

# Кольорова індикація
col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Поточний K", f"{final_k:.1f} мг/л")
    st.caption(f"GH = {gh} °dH")

with col_k2:
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}", 
              delta="норма 1.5–2.5", 
              delta_color="off")

with col_k3:
    if final_k < k_min:
        st.error(f"🚨 **КРИТИЧНИЙ ДЕФІЦИТ K**")
        st.write(f"K = {final_k:.1f} < {k_min:.0f} (мінімум при GH={gh})")
    elif final_k < k_opt_low:
        st.warning(f"⚠️ **Помірний дефіцит K**")
        st.write(f"K = {final_k:.1f} (оптимум {k_opt_low:.0f}–{k_opt_high:.0f})")
    elif final_k <= k_opt_high:
        st.success(f"✅ **Оптимальний K**")
        st.write(f"K = {final_k:.1f} в межах {k_opt_low:.0f}–{k_opt_high:.0f}")
    elif final_k <= k_max:
        st.warning(f"⚠️ **Початок антагонізму K**")
        st.write(f"K = {final_k:.1f} > {k_opt_high:.0f}")
    else:
        st.error(f"🚨 **КРИТИЧНИЙ ПЕРЕДОЗИР K**")
        st.write(f"K = {final_k:.1f} > {k_max:.0f} (максимум)")

# Детальний опис симптомів та рішень
with st.expander("📖 Діагностика K/GH: Симптоми та рішення"):
    tab_symptoms, tab_solutions, tab_chemistry = st.tabs(["🌿 Симптоми на рослинах", "💊 Рішення", "🧪 Хімічний механізм"])
    
    with tab_symptoms:
        st.markdown("""
        | Стан | Старе листя | Молоде листя | Корені |
        |------|-------------|--------------|--------|
        | **Дефіцит K** | Жовті/бурі краї, дірки | Дрібне, світле | Слабкі, тонкі |
        | **Надлишок K** | Темно-зелене, товсте | Скручене, білі кінчики | "Радікуліт" (гниль кінчиків) |
        | **Дефіцит Ca** (при надлишку K) | Норма | Деформоване, відмираючі точки росту | Короткі, товсті |
        """)
    
    with tab_solutions:
        if final_k < k_opt_low:
            st.info(f"**Рекомендація при дефіциті K (поточний {final_k:.1f} → ціль {k_opt_low:.0f}):**")
            st.write(f"• Додайте K₂SO₄ або KNO₃ до рівня {k_opt_low:.0f} мг/л")
            st.write(f"• Не підвищуйте K швидше ніж на 5 мг/л за день")
            st.write(f"• Перевірте, чи не занижений NO3 (зараз {final_no3:.1f})")
        elif final_k > k_opt_high:
            st.warning(f"**Рекомендація при надлишку K (поточний {final_k:.1f} → ціль {k_opt_high:.0f}):**")
            st.write(f"• Припиніть додавати K на 1-2 тижні")
            st.write(f"• Зробіть підміну 30-50% води")
            st.write(f"• Якщо використовуєте KNO₃ — замініть частину на NH₄NO₃ або сечовину")
            st.write(f"• Додайте Ca/Mg (підвищте GH до {gh} якщо нижче)")
        else:
            st.success("K/GH в ідеальному балансі. Продовжуйте поточне дозування.")
    
    with tab_chemistry:
        st.markdown("""
        ### ⚡ Конкуренція іонів
        
        **Механізм:**
        - K⁺, Ca²⁺, Mg²⁺ використовують одні й ті ж транспортні білки (іонні канали)
        - При високому K⁺ (K/GH > 2.5) канали насичуються K⁺
        - Ca²⁺ та Mg²⁺ не можуть потрапити в клітини → функціональний дефіцит
        
        **Формули запам'ятовування:**
        - Мінімум K = GH × 1.2
        - Оптимум K = GH × 1.8
        - Максимум K = GH × 2.8
        
        **Приклад для GH=6:**
        - K < 7.2 → дефіцит
        - K = 9–15 → оптимально
        - K > 16.8 → ризик антагонізму
        """)

# ======================== 8. РОЗУМНА РЕКОМЕНДАЦІЯ ДОБРИВ ДЛЯ K ========================
st.subheader("🎯 5. Розумна рекомендація корекції K")

# Визначаємо, чи потрібен азот
need_n = final_no3 < target_no3 * 0.9
k_target_optimal = (k_opt_low + k_opt_high) / 2

fertilizer_name, k_amount, explanation = recommend_k_fertilizer(
    final_k, k_target_optimal, need_n, final_no3, target_no3
)

if fertilizer_name:
    st.info(f"""
    **Рекомендоване добриво для K:** `{fertilizer_name}`
    
    - **Потрібно додати:** {k_amount:.1f} мг/л K
    - **Пояснення:** {explanation}
    - **Розрахунок дози для вашого об'єму ({tank_vol} л):**  
      {k_amount * tank_vol / 1000:.2f} грам {fertilizer_name} сухого порошку  
      Або розчиніть у воді та додайте протягом 2-3 днів
    """)
else:
    st.success("✅ K в оптимальному діапазоні, корекція не потрібна")

# ======================== 9. ЕКСПЕРТНИЙ АНАЛІЗ ========================
st.header("📝 6. Гідрохімічний експертний висновок")

co2_val = calculate_co2(kh, ph)
redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)
f_end = forecast[-1]

col_adv, col_metrics = st.columns([1.5, 1])

with col_adv:
    st.subheader("💡 Аналіз та рекомендації")
    
    # CO2
    if co2_val < 15:
        st.warning(f"💨 **Дефіцит CO2 ({co2_val:.1f} мг/л):** Рослини страждають, додайте CO2.")
    elif co2_val > co2_limit:
        st.error(f"🐟 **Небезпека! CO2 ({co2_val:.1f} мг/л):** Ризик гіпоксії для риб.")
    else:
        st.success(f"✅ CO2 в нормі: {co2_val:.1f} мг/л")
    
    # Redfield баланс
    if redfield_status == "дефіцит N":
        needed_n_ml = ((final_po4 * custom_redfield - final_no3) * tank_vol) / conc_n if conc_n > 0 else 0
        st.error(f"⚠️ **Дефіцит азоту:** Додайте {needed_n_ml:.1f} мл N добрива для балансу.")
    elif redfield_status == "дефіцит P":
        needed_p_ml = ((final_no3 / custom_redfield - final_po4) * tank_vol) / conc_p if conc_p > 0 else 0
        st.error(f"⚠️ **Дефіцит фосфору:** Додайте {needed_p_ml:.1f} мл P добрива.")
    else:
        st.success(f"✅ Redfield баланс: {redfield_ratio:.1f}:1 (ціль {custom_redfield}:1)")
    
    # Залізо
    if dose_fe_ml > 0:
        st.info(f"🧪 **Залізо:** Додано {add_fe:.2f} мг/л (≈ {add_fe*0.1:.2f} ppm Fe). Слідкуйте за іржею на обладнанні.")

with col_metrics:
    st.subheader("📊 Ключові метрики")
    st.metric("CO₂ (мг/л)", f"{co2_val:.1f}", delta="норма 20-30")
    st.metric("Redfield (N:P)", f"{redfield_ratio:.1f}:1", delta=f"ціль {custom_redfield}:1")
    st.metric("K/GH", f"{k_gh_ratio:.2f}", delta="норма 1.5-2.5")
    st.metric("TDS", f"{final_tds:.0f}", delta=f"{final_tds - target_tds:.0f} від цілі")

# ======================== 10. ПЛАН КОРЕКЦІЇ НА ПЕРІОД ========================
st.divider()
st.subheader("📅 7. План корекції добрив на наступний період")

ml_n_needed = get_ml_dose(f_end["NO3"], target_no3, conc_n, tank_vol)
ml_p_needed = get_ml_dose(f_end["PO4"], target_po4, conc_p, tank_vol)
ml_k_needed = get_ml_dose(f_end["K"], target_k, conc_k, tank_vol)

col_rec1, col_rec2, col_rec3 = st.columns(3)
with col_rec1:
    st.metric("Додатково N", f"{ml_n_needed/days:.1f} мл/день", delta=f"{ml_n_needed:.1f} мл за {days} днів")
with col_rec2:
    st.metric("Додатково P", f"{ml_p_needed/days:.2f} мл/день", delta=f"{ml_p_needed:.1f} мл за {days} днів")
with col_rec3:
    st.metric("Додатково K", f"{ml_k_needed/days:.1f} мл/день", delta=f"{ml_k_needed:.1f} мл за {days} днів")

# ======================== 11. ЗВІТ ДЛЯ КОПІЮВАННЯ ========================
st.divider()
st.subheader("📋 8. Звіт для журналу спостережень")

report = f"""=== TOXICODE AQUARIUM V9.1 REPORT ===
📅 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

【ОСНОВНІ ПАРАМЕТРИ】
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} °dH | KH: {kh} °dH | pH: {ph} | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л

【МАКРО】
NO3: {final_no3:.1f} / {target_no3} мг/л
PO4: {final_po4:.2f} / {target_po4} мг/л
K:   {final_k:.1f} / {target_k} мг/л

【БАЛАНСИ】
Redfield: {redfield_ratio:.1f}:1 (ціль {custom_redfield}:1) → {redfield_status}
K/GH: {k_gh_ratio:.2f} (норма 1.5-2.5)
Оптимум K для GH={gh}: {k_opt_low:.0f}–{k_opt_high:.0f} мг/л

【ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ】
NO3: {f_end['NO3']:.1f} → потрібно {ml_n_needed:.1f} мл N
PO4: {f_end['PO4']:.2f} → потрібно {ml_p_needed:.1f} мл P
K:   {f_end['K']:.1f}   → потрібно {ml_k_needed:.1f} мл K

【РЕКОМЕНДАЦІЯ ДОЗУВАННЯ (додатково до поточної дози)】
N: {ml_n_needed/days:.1f} мл/день
P: {ml_p_needed/days:.2f} мл/день
K: {ml_k_needed/days:.1f} мл/день

【K КОРЕКЦІЯ】
Рекомендоване добриво: {fertilizer_name if fertilizer_name else 'не потрібно'}
Додати K: {k_amount:.1f} мг/л
====================================="""

st.code(report, language="text")

# ======================== 12. ВАЛІДАЦІЯ ТА БЕЗПЕКА ========================
with st.expander("🛡️ Валідація та безпека (експертний режим)"):
    st.markdown("""
    | Перевірка | Статус | Критерій | Дія при порушенні |
    |-----------|--------|----------|-------------------|
    | **Передозування NO3** | ✅ Перевірено | NO3 < 40 мг/л | Підміна 30% води |
    | **Передозування PO4** | ✅ Перевірено | PO4 < 2.5 мг/л | Зменшити P, посилити фільтрацію |
    | **Осмотичний шок** | ⚠️ Контроль | TDS зміна < 30 за підміну | Повільніша підміна |
    | **CO₂ токсичність** | ✅ Перевірено | CO₂ < 35 мг/л | Аерація, зменшення CO₂ |
    | **K антагонізм** | ℹ️ Моніторинг | K/GH < 3.0 | Припинити K, додати Ca/Mg |
    """)
    
    warnings = []
    if final_no3 > 40:
        warnings.append("🚨 **КРИТИЧНО:** Високий NO3! Припиніть N добрива, зробіть підміну.")
    if final_po4 > 2.5:
        warnings.append("⚠️ Підвищений PO4 — ризик ціанобактерій та водоростей.")
    if co2_val > co2_limit:
        warnings.append("🚨 **НЕБЕЗПЕКА:** Зменште подачу CO2 негайно!")
    if final_k > k_max:
        warnings.append(f"⚠️ K перевищує максимум ({k_max:.0f}) — ризик блокування Ca/Mg.")
    
    for w in warnings:
        st.warning(w)
    
    if not warnings:
        st.success("✅ Всі параметри в безпечних межах")

st.caption("⚡ Toxicode V9.1 | K/GH контроль + розумне дозування K₂SO₄/KNO₃")
