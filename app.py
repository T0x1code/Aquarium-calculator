import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Toxicode Aquarium System V10.5", layout="wide")
st.title("🌿 Toxicode Aquarium System V10.5 — Максимальний контроль")

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
    except:
        return 0

def redfield_balance(no3, po4, target_ratio=15):
    """
    Коректний N:P через масу
    NO3 (мг/л) * 0.226 = N (мг/л)
    PO4 (мг/л) * 0.326 = P (мг/л)
    """
    if po4 <= 0:
        return "немає P", 0
    
    N = no3 * 0.226
    P = po4 * 0.326
    ratio = N / P if P > 0 else 0
    
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

def calculate_steady_state(daily_dose, wc_fraction):
    """Розрахунок рівноважної концентрації"""
    if wc_fraction <= 0:
        return daily_dose * 365
    return daily_dose / wc_fraction

def dose_to_mgl(dose_ml, conc_g_l, volume_l):
    """Перевід мл + г/л → мг/л"""
    if volume_l <= 0:
        return 0
    return (dose_ml * conc_g_l * 1000) / volume_l

def calculate_npk_ratio(n, p, k):
    """Розрахунок співвідношення NPK"""
    total = n + p + k
    if total == 0:
        return (0, 0, 0)
    return (n/total, p/total, k/total)

def algae_risk(no3, po4):
    """Оцінка ризику водоростей"""
    if po4 <= 0:
        return "Немає даних"
    N = no3 * 0.226
    P = po4 * 0.326
    ratio = N / P if P > 0 else 0
    
    if ratio < 8:
        return "🔴 Високий (дефіцит азоту стимулює ціанобактерії)"
    elif ratio > 25:
        return "🟠 Високий (дефіцит фосфору стимулює зелені водорості)"
    elif no3 > 30 or po4 > 1.5:
        return "🟡 Середній (надлишок макроелементів)"
    return "🟢 Низький"

def light_recommendation(co2, no3, po4):
    """Рекомендація інтенсивності світла"""
    if co2 < 20 or no3 < 5 or po4 < 0.2:
        return "💡 Низьке (50-70%, 6-8 годин)"
    elif co2 > 30 and no3 > 10 and po4 > 0.5:
        return "⚡ Високе (90-100%, 10-12 годин)"
    return "🌿 Середнє (70-90%, 8-10 годин)"

def save_to_history(params):
    """Збереження параметрів в історію"""
    record = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        **params
    }
    st.session_state.history.append(record)
    if len(st.session_state.history) > 50:
        st.session_state.history = st.session_state.history[-50:]

# ======================== SIDEBAR ========================
with st.sidebar:
    st.header("⚙️ Конфігурація")
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
    co2_min_opt = st.slider("Нижня межа CO₂ (мг/л)", 0, 100, 25)
    co2_max_opt = st.slider("Верхня межа CO₂ (мг/л)", 0, 100, 45)
    days = st.slider("Період прогнозу (днів)", 1, 30, 7)
    
    if st.button("📊 Зберегти показники"):
        st.success("Збережено!")

# ======================== 1. РЕМІНЕРАЛІЗАТОР ========================
st.header("💎 1. Ремінералізатор")
with st.expander("Розрахунок солей для підміни", expanded=False):
    col_rem1, col_rem2 = st.columns(2)
    
    with col_rem1:
        c_vol = st.number_input("Літрів осмосу", value=10.0, step=5.0, key="rem_vol")
        target_gh = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5)
        target_kh = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5)
        target_ca_mg = st.slider("Цільове Ca:Mg", 1.0, 6.0, 3.0, 0.5)
        
    with col_rem2:
        if target_ca_mg > 0:
            ratio_factor = target_ca_mg / 5.1 + 1 / 4.3
            mg_mgl = target_gh / ratio_factor if ratio_factor > 0 else 0
            ca_mgl = target_ca_mg * mg_mgl
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
        **Для {c_vol:.0f} л осмосу:**
        🧂 **{kh_from_caco3:.3f} г** CaCO₃
        🧂 **{cacl2_g:.3f} г** CaCl₂·2H₂O
        🧂 **{mgso4_g:.3f} г** MgSO₄·7H₂O
        """)

# ======================== 2. КАЛЬКУЛЯТОР СПОЖИВАННЯ ========================
st.header("📊 2. Калькулятор споживання")
consumption_results = {}

with st.expander("Аналіз минулого періоду"):
    t1, t2, t3 = st.tabs(["NO3", "PO4", "K"])
    
    def calc_real_cons(tab, name, key_p, is_po4=False):
        with tab:
            c1, c2, c3 = st.columns(3)
            
            if is_po4:
                p_test = c1.number_input(f"{name} (початок)", value=1.0, step=0.05, format="%.2f", key=f"p_{key_p}")
                c_test = c2.number_input(f"{name} (зараз)", value=0.5, step=0.05, format="%.2f", key=f"c_{key_p}")
            else:
                p_test = c1.number_input(f"{name} (початок)", value=15.0, step=0.5, format="%.1f", key=f"p_{key_p}")
                c_test = c2.number_input(f"{name} (зараз)", value=10.0, step=0.5, format="%.1f", key=f"c_{key_p}")
            
            with c3:
                st.markdown("**Внесено:**")
                dose_ml = st.number_input(f"мл", value=0.0, step=1.0, key=f"d_ml_{key_p}")
                if is_po4:
                    conc = st.number_input(f"г/л", value=5.0, step=0.5, key=f"conc_{key_p}")
                else:
                    conc = st.number_input(f"г/л", value=50.0, step=5.0, key=f"conc_{key_p}")
                added_mgl = dose_to_mgl(dose_ml, conc, tank_vol)
                st.caption(f"+{added_mgl:.2f} мг/л")
            
            cl1, cl2 = st.columns(2)
            ch_l = cl1.number_input(f"Підміна (л)", value=0.0, step=5.0, key=f"ch_l_{key_p}")
            days_between = cl2.number_input("Днів", value=7, min_value=1, step=1, key=f"d_{key_p}")
            
            pct_wc = (ch_l / tank_vol) if tank_vol > 0 else 0
            res = (p_test * (1 - pct_wc) + added_mgl - c_test) / days_between if days_between > 0 else 0
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"**Споживання:** {val:.2f} мг/л в день")
    
    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4", is_po4=True)
    calc_real_cons(t3, "K", "k")

# ======================== 3. ПОТОЧНИЙ СТАН ========================
st.header("📋 3. Поточні параметри")

col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("NO3 (мг/л)", value=10.0, step=0.5, format="%.1f")
    po4_now = st.number_input("PO4 (мг/л)", value=0.5, step=0.05, format="%.2f")
    k_now = st.number_input("K (мг/л)", value=10.0, step=0.5, format="%.1f")
    base_tds = st.number_input("TDS", value=150.0, step=5.0, format="%.0f")

with col2:
    gh = st.number_input("GH (°dH)", value=6, step=1)
    kh = st.number_input("KH (°dH)", value=2, step=1)
    ph_morning = st.number_input("pH (ранок)", value=7.2, step=0.1, format="%.1f")
    ph_evening = st.number_input("pH (вечір)", value=6.8, step=0.1, format="%.1f")
    co2_val = calculate_co2(kh, ph_evening)
    st.metric("CO₂", f"{co2_val:.1f} мг/л")

with col3:
    default_no3_cons = consumption_results.get('NO3', 2.0)
    default_po4_cons = consumption_results.get('PO4', 0.1)
    default_k_cons = consumption_results.get('K', 1.0)
    
    daily_no3 = st.number_input("Споживання NO3", value=float(default_no3_cons), step=0.1, format="%.1f")
    daily_po4 = st.number_input("Споживання PO4", value=float(default_po4_cons), step=0.05, format="%.2f")
    daily_k = st.number_input("Споживання K", value=float(default_k_cons), step=0.1, format="%.1f")

# ======================== 4. ПІДМІНА ========================
st.divider()
st.header("💧 4. Підміна")

c_change, c_dosing = st.columns(2)

with c_change:
    change_l = st.number_input("Літри підміни", value=50.0, step=1.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.metric("Відсоток", f"{pct*100:.1f}%")

with c_dosing:
    st.markdown("**Внесення ПІСЛЯ підміни:**")
    col_n, col_p, col_k = st.columns(3)
    
    with col_n:
        dose_after_n = st.number_input("N мл", value=0.0, step=1.0, key="after_n")
        conc_n_after = st.number_input("N г/л", value=50.0, key="conc_n_after")
        add_n_after = dose_to_mgl(dose_after_n, conc_n_after, tank_vol)
        st.caption(f"+{add_n_after:.1f}")
    
    with col_p:
        dose_after_p = st.number_input("P мл", value=0.0, step=0.5, key="after_p")
        conc_p_after = st.number_input("P г/л", value=5.0, key="conc_p_after")
        add_p_after = dose_to_mgl(dose_after_p, conc_p_after, tank_vol)
        st.caption(f"+{add_p_after:.2f}")
    
    with col_k:
        dose_after_k = st.number_input("K мл", value=0.0, step=1.0, key="after_k")
        conc_k_after = st.number_input("K г/л", value=20.0, key="conc_k_after")
        add_k_after = dose_to_mgl(dose_after_k, conc_k_after, tank_vol)
        st.caption(f"+{add_k_after:.1f}")

after_no3 = no3_now * (1 - pct) + add_n_after
after_po4 = po4_now * (1 - pct) + add_p_after
after_k = k_now * (1 - pct) + add_k_after

# ======================== 5. ДОЗУВАННЯ ========================
st.header("🧪 5. Дозування")

col_n, col_p, col_k = st.columns(3)

with col_n:
    dose_n = st.number_input("N мл/день", value=0.0, step=1.0, key="dose_n")
    conc_n = st.number_input("N г/л", value=50.0, key="conc_n")
    add_n = dose_to_mgl(dose_n, conc_n, tank_vol)

with col_p:
    dose_p = st.number_input("P мл/день", value=0.0, step=0.5, key="dose_p")
    conc_p = st.number_input("P г/л", value=5.0, key="conc_p")
    add_p = dose_to_mgl(dose_p, conc_p, tank_vol)

with col_k:
    dose_k = st.number_input("K мл/день", value=0.0, step=1.0, key="dose_k")
    conc_k = st.number_input("K г/л", value=20.0, key="conc_k")
    add_k = dose_to_mgl(dose_k, conc_k, tank_vol)

final_no3 = after_no3 + add_n
final_po4 = after_po4 + add_p
final_k = after_k + add_k

st.info(f"**Після всього:** NO₃={final_no3:.1f} | PO₄={final_po4:.2f} | K={final_k:.1f}")

# ======================== 6. STEADY STATE ========================
st.header("⚖️ 6. Steady State")

steady_no3 = calculate_steady_state(add_n, pct)
st.metric("Рівноважний NO₃", f"{steady_no3:.0f} мг/л", 
          help="Концентрація до якої прагне система при поточному дозуванні та підмінах")

# ======================== 7. ПРОГНОЗ ========================
st.header(f"📈 7. Прогноз на {days} днів")

# Коректний Redfield для стабільності
_, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)
if redfield_ratio > 0:
    stability = 1 / (1 + abs((redfield_ratio - custom_redfield) / custom_redfield))
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
    curr_n = max(0, curr_n + add_n - (daily_no3 * stability))
    curr_p = max(0, curr_p + add_p - (daily_po4 * stability))
    curr_k = max(0, curr_k + add_k - (daily_k * stability))

df_forecast = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_forecast)
st.caption(f"🎯 Коефіцієнт стабільності: {stability:.2f}")

# ======================== 8. K/GH АНАЛІЗ ========================
st.header("🧂 8. K/GH співвідношення")

k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("📐 Норми K/GH"):
    st.markdown(f"""
    **GH = {gh} °dH:**
    - Мінімум K: {k_opt_range['min']:.1f} мг/л
    - Оптимум: {k_opt_range['opt_low']:.0f}-{k_opt_range['opt_high']:.0f} мг/л
    - Максимум: {k_opt_range['max']:.1f} мг/л
    """)

col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Поточний K", f"{final_k:.1f} мг/л")
with col_k2:
    st.metric("K/GH", f"{k_gh_ratio:.2f}", delta="норма 1.5-2.5")
with col_k3:
    if final_k < k_opt_range['min']:
        st.error(f"🔴 Дефіцит K")
    elif final_k <= k_opt_range['opt_high']:
        st.success("✅ K в нормі")
    else:
        st.warning(f"🟡 Надлишок K")

# ======================== 9. ШІ АНАЛІЗ ========================
st.header("🤖 9. ШІ аналіз")

algae = algae_risk(final_no3, final_po4)
st.info(f"**🌊 Ризик водоростей:** {algae}")

light = light_recommendation(co2_val, final_no3, final_po4)
st.info(f"**💡 Світло:** {light}")

npk = calculate_npk_ratio(final_no3, final_po4, final_k)
st.caption(f"**NPK співвідношення:** {npk[0]:.1f} : {npk[1]:.1f} : {npk[2]:.1f}")

# ======================== 10. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.header("📅 10. План корекції")

f_end = forecast[-1]

delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4 - f_end["PO4"]
delta_k = target_k - f_end["K"]

if delta_no3 > 0:
    change_n = (delta_no3 * tank_vol) / (conc_n * days) if conc_n > 0 else 0
    new_dose_n = dose_n + change_n
    st.metric("N", f"{dose_n:.1f} → {new_dose_n:.1f} мл/день", delta=f"+{change_n:.1f}")
else:
    st.metric("N", f"{dose_n:.1f} мл/день", delta="норма")

if delta_po4 > 0:
    change_p = (delta_po4 * tank_vol) / (conc_p * days) if conc_p > 0 else 0
    new_dose_p = dose_p + change_p
    st.metric("P", f"{dose_p:.2f} → {new_dose_p:.2f} мл/день", delta=f"+{change_p:.2f}")
else:
    st.metric("P", f"{dose_p:.2f} мл/день", delta="норма")

if delta_k > 0:
    change_k = (delta_k * tank_vol) / (conc_k * days) if conc_k > 0 else 0
    new_dose_k = dose_k + change_k
    st.metric("K", f"{dose_k:.1f} → {new_dose_k:.1f} мл/день", delta=f"+{change_k:.1f}")
else:
    st.metric("K", f"{dose_k:.1f} мл/день", delta="норма")

# ======================== 11. ЗВІТ ========================
st.divider()
st.subheader("📋 11. Звіт")

report = f"""=== TOXICODE AQUARIUM V10.5 ===
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}

ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | CO₂: {co2_val:.1f} мг/л

МАКРО
NO3: {final_no3:.1f} / {target_no3}
PO4: {final_po4:.2f} / {target_po4}
K: {final_k:.1f} / {target_k}

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ
NO3: {f_end['NO3']:.1f}
PO4: {f_end['PO4']:.2f}
K: {f_end['K']:.1f}

РИЗИК ВОДОРОСТЕЙ
{algae}
====================================="""

st.code(report, language="text")

st.caption("⚡ Toxicode V10.5 | Steady State | Прогноз | K/GH | ШІ аналіз")
