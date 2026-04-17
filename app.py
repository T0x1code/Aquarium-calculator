import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Toxicode Aquarium System V9.6", layout="wide")
st.title("🌿 Toxicode Aquarium System V9.6 — Повний контроль + Збереження даних")

# ======================== ЗБЕРЕЖЕННЯ ПАРАМЕТРІВ ========================
CONFIG_FILE = "aquarium_config.json"

def load_config():
    """Завантажує збережені параметри з файлу"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    """Зберігає параметри у файл"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

# Завантажуємо збережені параметри
saved_config = load_config()

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
    """Оцінка співвідношення C:N:P:K"""
    if carbon_estimate > 0:
        c_ratio = carbon_estimate / po4 if po4 > 0 else 999
        c_status = "норма" if 200 < c_ratio < 600 else "дефіцит C" if c_ratio <= 200 else "надлишок C"
    else:
        c_status = "невідомо (потрібен тест CO₂)"
    
    np_ratio = no3 / po4 if po4 > 0 else 999
    if np_ratio < 10:
        np_status = "дефіцит N"
    elif np_ratio > 22:
        np_status = "дефіцит P"
    else:
        np_status = "баланс"
    
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
    if weekly_change_pct <= 0:
        return daily_dose * 365
    return (daily_dose * 7) / weekly_change_pct

def get_liebig_metrics(co2, no3, po4, k, fe, targets):
    """Нормалізація для графіка Лібіха (0.0 - 1.5)"""
    return {
        "C (CO₂)": min(co2 / 30.0, 1.5),
        "N (NO₃)": min(no3 / targets['no3'], 1.5) if targets['no3'] > 0 else 0,
        "P (PO₄)": min(po4 / targets['po4'], 1.5) if targets['po4'] > 0 else 0,
        "K": min(k / targets['k'], 1.5) if targets['k'] > 0 else 0,
        "Fe": min(fe / targets['fe'], 1.5) if targets['fe'] > 0 else 0
    }

# ======================== КНОПКА ЗБЕРЕЖЕННЯ ВСІХ ПАРАМЕТРІВ ========================
col_save1, col_save2, col_save3 = st.columns([3, 1, 1])
with col_save2:
    if st.button("💾 Зберегти всі параметри", use_container_width=True):
        # Збираємо всі поточні значення з session_state
        current_config = {
            'tank_vol': st.session_state.get('tank_vol', 200),
            'target_no3': st.session_state.get('target_no3', 15),
            'target_po4': st.session_state.get('target_po4', 1.0),
            'target_k': st.session_state.get('target_k', 15),
            'target_fe': st.session_state.get('target_fe', 0.1),
            'target_tds': st.session_state.get('target_tds', 120),
            'custom_redfield': st.session_state.get('custom_redfield', 15),
            'co2_min_opt': st.session_state.get('co2_min_opt', 25),
            'co2_max_opt': st.session_state.get('co2_max_opt', 45),
            'days': st.session_state.get('days', 7),
            'no3_now': st.session_state.get('no3_now', 10),
            'po4_now': st.session_state.get('po4_now', 0.5),
            'k_now': st.session_state.get('k_now', 10),
            'fe_now': st.session_state.get('fe_now', 0.05),
            'base_tds': st.session_state.get('base_tds', 150),
            'gh': st.session_state.get('gh', 6),
            'kh': st.session_state.get('kh', 2),
            'ph': st.session_state.get('ph', 6.8),
            'ca_calc': st.session_state.get('ca_calc', 30),
            'mg_calc': st.session_state.get('mg_calc', 10),
            'daily_no3': st.session_state.get('daily_no3', 2.0),
            'daily_po4': st.session_state.get('daily_po4', 0.1),
            'daily_k': st.session_state.get('daily_k', 1.0),
            'change_l': st.session_state.get('change_l', 50),
            'water_no3': st.session_state.get('water_no3', 0),
            'water_po4': st.session_state.get('water_po4', 0),
            'water_k': st.session_state.get('water_k', 0),
            'water_tds': st.session_state.get('water_tds', 110),
            'conc_n': st.session_state.get('conc_n', 50),
            'current_dose_n_ml': st.session_state.get('current_dose_n_ml', 0),
            'conc_p': st.session_state.get('conc_p', 5),
            'current_dose_p_ml': st.session_state.get('current_dose_p_ml', 0),
            'conc_k': st.session_state.get('conc_k', 20),
            'current_dose_k_ml': st.session_state.get('current_dose_k_ml', 0),
            'conc_fe': st.session_state.get('conc_fe', 1),
            'current_dose_fe_ml': st.session_state.get('current_dose_fe_ml', 0),
            'target_gh': st.session_state.get('target_gh', 6),
            'target_kh': st.session_state.get('target_kh', 2),
            'target_ca_mg_ratio': st.session_state.get('target_ca_mg_ratio', 3),
            'rem_vol': st.session_state.get('rem_vol', 10)
        }
        if save_config(current_config):
            st.toast("✅ Параметри збережено!", icon="✅")
        else:
            st.error("❌ Помилка збереження")

with col_save3:
    if st.button("🔄 Скинути всі", use_container_width=True):
        # Очищаємо session_state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.divider()

# ======================== SIDEBAR — ГЛОБАЛЬНА КОНФІГУРАЦІЯ ========================
with st.sidebar:
    st.header("📏 Конфігурація системи")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=saved_config.get('tank_vol', 200.0), step=1.0, key="tank_vol")
    
    st.divider()
    st.subheader("🎯 Цільові показники")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=saved_config.get('target_no3', 15.0), step=1.0, key="target_no3")
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=saved_config.get('target_po4', 1.0), step=0.1, key="target_po4")
    target_k = st.number_input("Ціль K (мг/л)", value=saved_config.get('target_k', 15.0), step=1.0, key="target_k")
    target_fe = st.number_input("Ціль Fe (мг/л)", value=saved_config.get('target_fe', 0.1), step=0.05, key="target_fe", help="Залізо для рослин")
    target_tds = st.number_input("Ціль TDS", value=saved_config.get('target_tds', 120.0), step=5.0, key="target_tds")
    
    st.divider()
    st.subheader("⚙️ Розширені налаштування")
    custom_redfield = st.slider("Бажана пропорція Редфілда (N:P)", 5, 30, saved_config.get('custom_redfield', 15), key="custom_redfield")
    
    co2_min_opt = st.slider("Нижня межа CO₂ (мг/л)", 0, 100, saved_config.get('co2_min_opt', 25), key="co2_min_opt")
    co2_max_opt = st.slider("Верхня межа CO₂ (мг/л)", 0, 100, saved_config.get('co2_max_opt', 45), key="co2_max_opt")
    
    days = st.slider("Період прогнозу (днів)", 1, 14, saved_config.get('days', 7), key="days")

# ======================== 1. РЕМІНЕРАЛІЗАТОР (РОЗУМНИЙ РОЗРАХУНОК) ========================
st.header("💎 1. Ремінералізатор (Розумний розрахунок)")
with st.expander("Розрахунок солей для підміни", expanded=True):
    st.markdown("""
    **Як це працює:**  
    Ви задаєте бажані параметри води (GH, KH, Ca:Mg), а система розраховує точну кількість солей.
    """)
    
    col_rem1, col_rem2 = st.columns(2)
    
    with col_rem1:
        c_vol = st.number_input("Літрів свіжої води (осмос)", value=saved_config.get('rem_vol', 10.0), step=5.0, key="rem_vol")
        
        st.divider()
        st.subheader("🎯 Цільові параметри")
        
        target_gh = st.slider("Цільовий GH (°dH)", min_value=1.0, max_value=20.0, value=saved_config.get('target_gh', 6.0), step=0.5, key="target_gh",
                              help="Загальна жорсткість (кальцій + магній)")
        
        target_kh = st.slider("Цільовий KH (°dH)", min_value=0.0, max_value=15.0, value=saved_config.get('target_kh', 2.0), step=0.5, key="target_kh",
                              help="Карбонатна жорсткість (буферна ємність)")
        
        target_ca_mg_ratio = st.slider("Цільове співвідношення Ca:Mg", min_value=1.0, max_value=6.0, value=saved_config.get('target_ca_mg_ratio', 3.0), step=0.5, key="target_ca_mg_ratio",
                                       help="Оптимальне співвідношення для більшості рослин 3:1")
        
    with col_rem2:
        st.subheader("🧪 Розрахований склад")
        
        # Хімічні константи
        kh_from_caco3 = (target_kh * 17.86 * c_vol / 1000)
        ca_from_caco3_g = kh_from_caco3 * 0.4
        
        # Розрахунок необхідного Ca та Mg
        total_ca_mg_mgl = target_gh * 7.14
        ratio_factor = target_ca_mg_ratio / 5.1 + 1 / 4.3
        mg_mgl = target_gh / ratio_factor
        ca_mgl = target_ca_mg_ratio * mg_mgl
        
        total_ca_g = ca_mgl * c_vol / 1000
        total_mg_g = mg_mgl * c_vol / 1000
        
        remaining_ca_g = max(0, total_ca_g - ca_from_caco3_g)
        cacl2_g = remaining_ca_g / 0.273 if remaining_ca_g > 0 else 0
        mgso4_g = total_mg_g / 0.0986 if total_mg_g > 0 else 0
        
        st.success(f"""
        **Для {c_vol:.0f} л осмосу додай:**
        
        🧂 **{kh_from_caco3:.3f} г** $CaCO_3$ (кальцій карбонат)
        🧂 **{cacl2_g:.3f} г** $CaCl_2 \\cdot 2H_2O$ (кальцій хлорид)
        🧂 **{mgso4_g:.3f} г** $MgSO_4 \\cdot 7H_2O$ (магній сульфат)
        """)
        
        # Прогноз параметрів
        st.divider()
        st.subheader("📊 Прогнозовані параметри")
        
        predicted_ca_mgl = (ca_from_caco3_g + remaining_ca_g) * 1000 / c_vol
        predicted_mg_mgl = total_mg_g * 1000 / c_vol
        predicted_gh = (predicted_ca_mgl / 5.1) + (predicted_mg_mgl / 4.3)
        predicted_ratio = predicted_ca_mgl / predicted_mg_mgl if predicted_mg_mgl > 0 else 0
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.metric("GH", f"{predicted_gh:.1f}°dH", delta=f"ціль {target_gh:.1f}")
        with col_p2:
            st.metric("KH", f"{target_kh:.1f}°dH", delta="від CaCO₃")
        with col_p3:
            st.metric("Ca:Mg", f"{predicted_ratio:.1f}:1", delta=f"ціль {target_ca_mg_ratio:.1f}:1")

# ======================== 2. КАЛЬКУЛЯТОР РЕАЛЬНОГО СПОЖИВАННЯ ========================
st.header("📉 2. Калькулятор реального споживання (на основі тестів)")
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

# ======================== 3. ПОТОЧНИЙ СТАН ========================
st.header("📋 3. Поточні параметри води")
col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("NO3 (мг/л)", value=saved_config.get('no3_now', 10.0), step=1.0, key="no3_now")
    po4_now = st.number_input("PO4 (мг/л)", value=saved_config.get('po4_now', 0.5), step=0.1, key="po4_now")
    k_now = st.number_input("K (мг/л)", value=saved_config.get('k_now', 10.0), step=1.0, key="k_now")
    fe_now = st.number_input("Fe (мг/л)", value=saved_config.get('fe_now', 0.05), step=0.01, key="fe_now", help="Залізо")
    base_tds = st.number_input("TDS", value=saved_config.get('base_tds', 150.0), step=5.0, key="base_tds")

with col2:
    gh = st.number_input("GH (°dH)", value=saved_config.get('gh', 6), step=1, key="gh")
    kh = st.number_input("KH (°dH)", value=saved_config.get('kh', 2), step=1, key="kh")
    ph = st.number_input("pH", value=saved_config.get('ph', 6.8), step=0.1, key="ph")
    
    st.divider()
    st.caption("🧪 Співвідношення Ca:Mg")
    ca_calc = st.number_input("Ca (мг/л)", value=saved_config.get('ca_calc', 30.0), step=5.0, key="ca_calc")
    mg_calc = st.number_input("Mg (мг/л)", value=saved_config.get('mg_calc', 10.0), step=2.0, key="mg_calc")
    ca_mg_ratio = ca_calc / mg_calc if mg_calc > 0 else 0
    if 2.5 <= ca_mg_ratio <= 3.5:
        st.success(f"✅ Ca:Mg = {ca_mg_ratio:.1f}:1 (ціль 3:1)")
    else:
        st.warning(f"⚠️ Ca:Mg = {ca_mg_ratio:.1f}:1 (коригуй ремінералізатором)")

with col3:
    default_no3_cons = consumption_results.get('NO3', saved_config.get('daily_no3', 2.0))
    default_po4_cons = consumption_results.get('PO4', saved_config.get('daily_po4', 0.1))
    default_k_cons = consumption_results.get('K', saved_config.get('daily_k', 1.0))
    
    daily_no3 = st.number_input("Споживання NO3 (мг/л/день)", value=default_no3_cons, step=0.1, key="daily_no3")
    daily_po4 = st.number_input("Споживання PO4 (мг/л/день)", value=default_po4_cons, step=0.1, key="daily_po4")
    daily_k = st.number_input("Споживання K (мг/л/день)", value=default_k_cons, step=0.1, key="daily_k")

# ======================== 4. ПІДМІНА ВОДИ ========================
st.divider()
st.header("💧 4. Підміна води")
c_change, c_quality = st.columns(2)

with c_change:
    change_l = st.number_input("Літри підміни", value=saved_config.get('change_l', 50.0), step=1.0, key="change_l")
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.metric("Відсоток підміни", f"{pct*100:.1f}%")
    
    weekly_change_pct = pct * 7 if pct > 0 else 0
    steady_no3 = calculate_steady_state(daily_no3, weekly_change_pct)
    st.caption(f"📊 **Steady State NO₃:** {steady_no3:.0f} мг/л (рівноважна концентрація)")

with c_quality:
    water_no3 = st.number_input("NO3 у новій воді (мг/л)", value=saved_config.get('water_no3', 0.0), step=0.5, key="water_no3")
    water_po4 = st.number_input("PO4 у новій воді (мг/л)", value=saved_config.get('water_po4', 0.0), step=0.1, key="water_po4")
    water_k = st.number_input("K у новій воді (мг/л)", value=saved_config.get('water_k', 0.0), step=1.0, key="water_k")
    water_tds = st.number_input("TDS нової води", value=saved_config.get('water_tds', 110.0), step=5.0, key="water_tds")

after_no3 = no3_now * (1 - pct) + water_no3 * pct
after_po4 = po4_now * (1 - pct) + water_po4 * pct
after_k = k_now * (1 - pct) + water_k * pct
after_tds = base_tds * (1 - pct) + water_tds * pct
after_fe = fe_now * (1 - pct)

# ======================== 5. ДОЗУВАННЯ ДОБРИВ ========================
st.header("🧪 5. Дозування добрив")
st.caption("Концентрація готового розчину (г/л) та поточна доза (мл/день)")

cd_n, cd_p, cd_k, cd_fe = st.columns(4)

with cd_n:
    conc_n = st.number_input("N (NO3) г/л", value=saved_config.get('conc_n', 50.0), step=5.0, key="conc_n")
    current_dose_n_ml = st.number_input("Поточна доза N мл/день", value=saved_config.get('current_dose_n_ml', 0.0), step=1.0, key="current_dose_n_ml")
    add_no3 = (current_dose_n_ml * conc_n) / tank_vol

with cd_p:
    conc_p = st.number_input("P (PO4) г/л", value=saved_config.get('conc_p', 5.0), step=0.5, key="conc_p")
    current_dose_p_ml = st.number_input("Поточна доза P мл/день", value=saved_config.get('current_dose_p_ml', 0.0), step=0.5, key="current_dose_p_ml")
    add_po4 = (current_dose_p_ml * conc_p) / tank_vol

with cd_k:
    conc_k = st.number_input("K г/л", value=saved_config.get('conc_k', 20.0), step=2.0, key="conc_k")
    current_dose_k_ml = st.number_input("Поточна доза K мл/день", value=saved_config.get('current_dose_k_ml', 0.0), step=1.0, key="current_dose_k_ml")
    add_k = (current_dose_k_ml * conc_k) / tank_vol

with cd_fe:
    conc_fe = st.number_input("Fe г/л", value=saved_config.get('conc_fe', 1.0), step=0.1, key="conc_fe")
    current_dose_fe_ml = st.number_input("Поточна доза Fe мл/день", value=saved_config.get('current_dose_fe_ml', 0.0), step=0.5, key="current_dose_fe_ml")
    add_fe = (current_dose_fe_ml * conc_fe) / tank_vol

final_no3 = after_no3 + add_no3
final_po4 = after_po4 + add_po4
final_k = after_k + add_k
final_fe = after_fe + add_fe
final_tds = after_tds + (add_no3 + add_po4 + add_k + add_fe) * 0.5

# ======================== 6. СТАБІЛЬНІСТЬ ТА АДАПТАЦІЯ ========================
ratio_now = final_no3 / final_po4 if final_po4 > 0 else 0
stability = 1 / (1 + abs((ratio_now - custom_redfield) / custom_redfield))
st.caption(f"🎚️ **Коефіцієнт стабільності (Redfield):** {stability:.2f} — впливає на прогноз споживання")

# ======================== 7. ЗАКОН МІНІМУМУ ЛІБІХА ========================
st.header("⚖️ 6. Закон Мінімуму Лібіха")
st.caption("Візуалізація лімітуючих факторів — що зараз 'гальмує' акваріум")

co2_val = calculate_co2(kh, ph)
targets_dict = {'no3': target_no3, 'po4': target_po4, 'k': target_k, 'fe': target_fe}
l_metrics = get_liebig_metrics(co2_val, final_no3, final_po4, final_k, final_fe, targets_dict)

col_ch, col_txt = st.columns([2, 1])
with col_ch:
    st.bar_chart(pd.Series(l_metrics))
with col_txt:
    lim_factor = min(l_metrics, key=l_metrics.get)
    st.error(f"**Лімітуючий фактор:** {lim_factor}")
    st.caption("Значення < 1.0 — дефіцит, > 1.0 — надлишок")

# ======================== 8. ПРОГНОЗ НА days ДНІВ ========================
st.header(f"📈 7. Динамічний прогноз на {days} днів")

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

# ======================== 9. C:N:P:K АНАЛІЗ ========================
st.header("⚖️ 8. C:N:P:K співвідношення — повний баланс")
st.caption("Для здорових рослин потрібен баланс всіх чотирьох елементів: Вуглець, Азот, Фосфор, Калій")

cnpk_status = calculate_cnpk_status(co2_val, final_no3, final_po4, final_k)

col_c, col_n, col_p, col_k_bal = st.columns(4)

with col_c:
    st.metric("CO₂ (C)", f"{co2_val:.1f} мг/л", delta="C джерело", delta_color="off")
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

# ======================== 10. K/GH АНАЛІЗ ========================
st.header("🧂 9. K/GH співвідношення — контроль антагонізму")

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
    
    > **Запам'ятайте:** K_ціль (мг/л) = GH × 1.8
    > 
    > Допустимий діапазон: GH × 1.5 до GH × 2.5
    """)

col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Поточний K", f"{final_k:.1f} мг/л")
    st.caption(f"GH = {gh} °dH")

with col_k2:
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}")

with col_k3:
    if final_k < k_opt_range['min']:
        st.error("🚨 КРИТИЧНИЙ ДЕФІЦИТ K")
        st.write(f"Потрібно підняти на {k_opt_range['min'] - final_k:.1f} мг/л")
    elif final_k < k_opt_range['opt_low']:
        st.warning("⚠️ Помірний дефіцит K")
        st.write(f"Підніміть до {k_opt_range['opt_low']:.0f}-{k_opt_range['opt_high']:.0f} мг/л")
    elif final_k <= k_opt_range['opt_high']:
        st.success("✅ Оптимальний K")
    elif final_k <= k_opt_range['max']:
        st.warning("⚠️ Початок антагонізму K")
        st.write(f"Знизьте K на {final_k - k_opt_range['opt_high']:.1f} мг/л")
    else:
        st.error("🚨 КРИТИЧНИЙ ПЕРЕДОЗИР K")
        st.write(f"Терміново знизьте K на {final_k - k_opt_range['max']:.1f} мг/л")

# ======================== 11. ПЛАН КОРЕКЦІЇ ========================
st.divider()
st.header("📅 10. План корекції дозування")

f_end = forecast[-1]

delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4 - f_end["PO4"]
delta_k = target_k - f_end["K"]

if delta_no3 > 0:
    daily_delta_no3 = delta_no3 / days
    change_n_ml = (daily_delta_no3 * tank_vol) / conc_n if conc_n > 0 else 0
    new_dose_n = current_dose_n_ml + change_n_ml
elif delta_no3 < 0:
    daily_delta_no3 = abs(delta_no3) / days
    reduce_n_ml = (daily_delta_no3 * tank_vol) / conc_n if conc_n > 0 else 0
    new_dose_n = max(0, current_dose_n_ml - reduce_n_ml)
else:
    new_dose_n = current_dose_n_ml

if delta_po4 > 0:
    daily_delta_po4 = delta_po4 / days
    change_p_ml = (daily_delta_po4 * tank_vol) / conc_p if conc_p > 0 else 0
    new_dose_p = current_dose_p_ml + change_p_ml
elif delta_po4 < 0:
    daily_delta_po4 = abs(delta_po4) / days
    reduce_p_ml = (daily_delta_po4 * tank_vol) / conc_p if conc_p > 0 else 0
    new_dose_p = max(0, current_dose_p_ml - reduce_p_ml)
else:
    new_dose_p = current_dose_p_ml

if delta_k > 0:
    daily_delta_k = delta_k / days
    change_k_ml = (daily_delta_k * tank_vol) / conc_k if conc_k > 0 else 0
    new_dose_k = current_dose_k_ml + change_k_ml
elif delta_k < 0:
    daily_delta_k = abs(delta_k) / days
    reduce_k_ml = (daily_delta_k * tank_vol) / conc_k if conc_k > 0 else 0
    new_dose_k = max(0, current_dose_k_ml - reduce_k_ml)
else:
    new_dose_k = current_dose_k_ml

col_rec1, col_rec2, col_rec3 = st.columns(3)

with col_rec1:
    st.subheader("🧪 Азот (N)")
    st.metric("Поточна доза", f"{current_dose_n_ml:.1f} мл/день")
    if delta_no3 > 0:
        st.warning(f"📈 Дефіцит NO₃: {delta_no3:.1f} мг/л за {days} днів")
        st.info(f"➕ Додайте +{change_n_ml:.1f} мл/день")
    elif delta_no3 < 0:
        st.warning(f"📉 Надлишок NO₃: {abs(delta_no3):.1f} мг/л за {days} днів")
        st.info(f"➖ Зменште на {reduce_n_ml:.1f} мл/день")
    else:
        st.success("✅ NO₃ в нормі")
    st.metric("Нова доза", f"{new_dose_n:.1f} мл/день")

with col_rec2:
    st.subheader("💧 Фосфор (P)")
    st.metric("Поточна доза", f"{current_dose_p_ml:.2f} мл/день")
    if delta_po4 > 0:
        st.warning(f"📈 Дефіцит PO₄: {delta_po4:.2f} мг/л за {days} днів")
        st.info(f"➕ Додайте +{change_p_ml:.2f} мл/день")
    elif delta_po4 < 0:
        st.warning(f"📉 Надлишок PO₄: {abs(delta_po4):.2f} мг/л за {days} днів")
        st.info(f"➖ Зменште на {reduce_p_ml:.2f} мл/день")
    else:
        st.success("✅ PO₄ в нормі")
    st.metric("Нова доза", f"{new_dose_p:.2f} мл/день")

with col_rec3:
    st.subheader("🌾 Калій (K)")
    st.metric("Поточна доза", f"{current_dose_k_ml:.1f} мл/день")
    if delta_k > 0:
        st.warning(f"📈 Дефіцит K: {delta_k:.1f} мг/л за {days} днів")
        st.info(f"➕ Додайте +{change_k_ml:.1f} мл/день")
    elif delta_k < 0:
        st.warning(f"📉 Надлишок K: {abs(delta_k):.1f} мг/л за {days} днів")
        st.info(f"➖ Зменште на {reduce_k_ml:.1f} мл/день")
    else:
        st.success("✅ K в нормі")
    st.metric("Нова доза", f"{new_dose_k:.1f} мл/день")

st.caption(f"""
💡 Як читати рекомендації:
- Дефіцит/надлишок вказано за {days} днів
- Корекція розподілена на {days} днів — це ДОБОВА зміна дози
- Змінюйте дозування поступово, не більше ніж на 20% за день
""")

# ======================== 12. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("📝 11. Експертний висновок")

redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
    st.subheader("📊 Стан системи")
    
    if co2_val < co2_min_opt:
        st.warning(f"💨 CO₂: {co2_val:.1f} мг/л — дефіцит (норма {co2_min_opt}-{co2_max_opt})")
    elif co2_val > co2_max_opt:
        st.error(f"🐟 CO₂: {co2_val:.1f} мг/л — надлишок (норма {co2_min_opt}-{co2_max_opt})")
    else:
        st.success(f"✅ CO₂: {co2_val:.1f} мг/л — норма")
    
    if redfield_status == "дефіцит N":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — дефіцит азоту (ціль {custom_redfield}:1)")
    elif redfield_status == "дефіцит P":
        st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — дефіцит фосфору (ціль {custom_redfield}:1)")
    else:
        st.success(f"✅ N:P = {redfield_ratio:.1f}:1 — баланс")
    
    if final_k < k_opt_range['opt_low']:
        st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — дефіцит K")
    elif final_k > k_opt_range['opt_high']:
        st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — надлишок K")
    else:
        st.success(f"✅ K/GH = {k_gh_ratio:.2f} — норма")

with col_summary2:
    st.subheader(f"📋 Прогноз через {days} днів")
    st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л", delta=f"{f_end['NO3'] - target_no3:.1f}")
    st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л", delta=f"{f_end['PO4'] - target_po4:.2f}")
    st.metric("K", f"{f_end['K']:.1f} мг/л", delta=f"{f_end['K'] - target_k:.1f}")

# ======================== 13. ЗВІТ ========================
st.divider()
st.subheader("📋 12. Звіт для журналу")

report = f"""=== TOXICODE AQUARIUM V9.6 REPORT ===
📅 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

ОСНОВНІ ПАРАМЕТРИ
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | pH: {ph} | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л (норма {co2_min_opt}-{co2_max_opt})
Ca:Mg = {ca_mg_ratio:.1f}:1

МАКРО
NO3: {final_no3:.1f} / {target_no3} мг/л
PO4: {final_po4:.2f} / {target_po4} мг/л
K:   {final_k:.1f} / {target_k} мг/л
Fe:  {final_fe:.2f} / {target_fe} мг/л

C:N:P:K
N:P = {cnpk_status['np_ratio']:.1f}:1 -> {cnpk_status['np_status']}
K:N = {cnpk_status['kn_ratio']:.2f}:1 -> {cnpk_status['k_status']}
Лімітуючий фактор: {lim_factor}

K/GH
K/GH = {k_gh_ratio:.2f} (норма 1.5-2.5)
Оптимум K для GH={gh}: {k_opt_range['opt_low']:.0f}-{k_opt_range['opt_high']:.0f} мг/л

ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ
NO3: {f_end['NO3']:.1f} мг/л
PO4: {f_end['PO4']:.2f} мг/л
K:   {f_end['K']:.1f} мг/л

РЕКОМЕНДАЦІЯ ЗМІНИ ДОЗИ
N: {current_dose_n_ml:.1f} -> {new_dose_n:.1f} мл/день
P: {current_dose_p_ml:.2f} -> {new_dose_p:.2f} мл/день
K: {current_dose_k_ml:.1f} -> {new_dose_k:.1f} мл/день
====================================="""

st.code(report, language="text")

# ======================== 14. ВАЛІДАЦІЯ ========================
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
    if ca_mg_ratio < 2 or ca_mg_ratio > 4:
        st.warning("⚠️ Співвідношення Ca:Mg далеке від 3:1 — скоригуйте ремінералізатор")

st.caption("⚡ Toxicode V9.6 | Повний контроль C:N:P:K | Закон Лібіха | Автозбереження параметрів")
