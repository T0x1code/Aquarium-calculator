import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V8.3", layout="wide")
st.title("🌿 Toxicode Aquarium System V8.3 Ultimate")

# ---------------- HELPER ----------------
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def get_ml_dose(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0.0

# ---------------- 1. SIDEBAR ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0, step=1.0)

    st.divider()
    st.subheader("🎯 Цільові значення")
    target_no3 = st.number_input("Ціль NO3", value=15.0)
    target_po4 = st.number_input("Ціль PO4", value=1.0)
    target_k = st.number_input("Ціль K", value=15.0)

    st.divider()
    st.subheader("⚙️ Аналітика та Модель")
    custom_redfield = st.slider("Редфілд (N:1P)", 5, 30, 15)
    days = st.slider("Прогноз (днів)", 1, 14, 7)
    data_quality = st.slider("Якість даних (Data Quality)", 0.5, 1.0, 0.85)

# ---------------- 2. СПОЖИВАННЯ (РЕАЛЬНЕ) ----------------
st.header("📉 1. Калькулятор споживання")
consumption_results = {}

with st.expander("Аналіз минулого періоду (на основі тестів)"):
    t_tabs = st.tabs(["NO3", "PO4", "K"])
    
    def calc_cons(tab, name, key):
        with tab:
            c1, c2, c3 = st.columns(3)
            start = c1.number_input(f"{name} старт", value=15.0, key=f"s_{key}")
            end = c2.number_input(f"{name} зараз", value=10.0, key=f"e_{key}")
            added = c3.number_input(f"Внесено {name}", value=0.0, key=f"a_{key}")

            c4, c5 = st.columns(2)
            w_change = c4.number_input("Підміна (л)", value=0.0, key=f"w_{key}")
            d_local = c5.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key}")

            pct_local = w_change / tank_vol if tank_vol > 0 else 0
            # Розрахунок споживання з урахуванням якості даних (V8.2 logic)
            cons = ((start * (1 - pct_local) + added - end) / d_local) * data_quality
            val = max(cons, 0)
            consumption_results[name] = val
            st.info(f"**Реальне споживання {name}:** {val:.2f} мг/л/д")

    calc_cons(t_tabs[0], "NO3", "no3")
    calc_cons(t_tabs[1], "PO4", "po4")
    calc_cons(t_tabs[2], "K", "k")

# ---------------- 3. ПОТОЧНИЙ СТАН ----------------
st.header("📋 2. Поточний стан")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Сьогоднішні тести")
    no3_now = st.number_input("Тест NO3", value=10.0)
    po4_now = st.number_input("Тест PO4", value=0.5)
    k_now = st.number_input("Тест K", value=10.0)
    base_tds = st.number_input("Поточний TDS", value=150.0)

with col2:
    st.subheader("Параметри води")
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=3)
    ph = st.number_input("pH", value=6.8)

with col3:
    st.subheader("Базове споживання")
    daily_no3 = st.number_input("Споживання NO3 (д)", value=consumption_results.get("NO3", 2.0))
    daily_po4 = st.number_input("Споживання PO4 (д)", value=consumption_results.get("PO4", 0.1))
    daily_k = st.number_input("Споживання K (д)", value=consumption_results.get("K", 1.0))

# Стабілізація через Redfield (V8.2 logic)
ratio_now = no3_now / po4_now if po4_now > 0 else 0
ref_error = (ratio_now - custom_redfield) / custom_redfield
stability = 1 / (1 + abs(ref_error))

# Коригуємо щоденне споживання для прогнозу
adj_daily_no3 = daily_no3 * stability
adj_daily_po4 = daily_po4 * stability
adj_daily_k = daily_k * stability

# ---------------- 4. ПІДМІНА ТА ДОЗУВАННЯ ----------------
st.divider()
c_act1, c_act2 = st.columns([1, 2])

with c_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Об'єм підміни (л)", value=50.0)
    new_tds = st.number_input("TDS свіжої води", value=110.0)
    
    pct_main = change_l / tank_vol if tank_vol > 0 else 0
    after_no3, after_po4, after_k = no3_now*(1-pct_main), po4_now*(1-pct_main), k_now*(1-pct_main)
    after_tds = base_tds * (1-pct_main) + (new_tds * pct_main)

with c_act2:
    st.header("🧪 Дозування")
    cd1, cd2, cd3 = st.columns(3)
    c_n, d_n = cd1.number_input("N розчин г/л", value=50.0), cd1.number_input("Внести N мл", value=0.0)
    c_p, d_p = cd2.number_input("P розчин г/л", value=5.0), cd2.number_input("Внести P мл", value=0.0)
    c_k, d_k = cd3.number_input("K розчин г/л", value=20.0), cd3.number_input("Внести K мл", value=0.0)

# Стан ПІСЛЯ внесення
start_no3 = after_no3 + (d_n * c_n / tank_vol)
start_po4 = after_po4 + (d_p * c_p / tank_vol)
start_k = after_k + (d_k * c_k / tank_vol)

# ---------------- 5. ПРОГНОЗ (динамічний) ----------------
st.header("📈 3. Динамічний прогноз (з внесенням і споживанням)")

forecast = []

curr_n = start_no3
curr_p = start_po4
curr_k = start_k

# щоденне внесення (можеш потім винести в UI)
daily_add_n = (d_n * c_n / tank_vol) if tank_vol > 0 else 0
daily_add_p = (d_p * c_p / tank_vol) if tank_vol > 0 else 0
daily_add_k = (d_k * c_k / tank_vol) if tank_vol > 0 else 0

warn_n = None
warn_p = None
warn_k = None

for d in range(days + 1):

    # запис стану ДО змін
    forecast.append({
        "День": d,
        "NO3": curr_n,
        "PO4": curr_p,
        "K": curr_k
    })

    # перевірка на виснаження
    if warn_n is None and curr_n <= 0:
        warn_n = d
    if warn_p is None and curr_p <= 0:
        warn_p = d
    if warn_k is None and curr_k <= 0:
        warn_k = d

    # 1) споживання
    curr_n -= adj_daily_no3
    curr_p -= adj_daily_po4
    curr_k -= adj_daily_k

    # 2) внесення (щоденне, якщо дозування задано)
    curr_n += daily_add_n
    curr_p += daily_add_p
    curr_k += daily_add_k

    # 3) фізичні межі
    curr_n = clamp(curr_n, 0, 100)
    curr_p = clamp(curr_p, 0, 10)
    curr_k = clamp(curr_k, 0, 100)

df_forecast = pd.DataFrame(forecast)
st.line_chart(df_forecast.set_index("День"))

st.subheader("⚠️ Аналіз виснаження")

if warn_n is not None:
    st.error(f"NO3 може закінчитись на день {warn_n}")

if warn_p is not None:
    st.error(f"PO4 може закінчитись на день {warn_p}")

if warn_k is not None:
    st.warning(f"K може закінчитись на день {warn_k}")

# ---------------- 6. АНАЛІЗ ТА ПОРАДИ ----------------
st.header("📊 4. Аналіз та Рекомендації")
co2_val = 3 * kh * (10 ** (7 - ph))
ratio_final = start_no3 / start_po4 if start_po4 > 0 else 0
k_min = gh * 1.5

col_adv, col_rep = st.columns([1.3, 1])

with col_adv:
    st.subheader("💡 План дій")
    
    # Редфілд-корекція
    if ratio_final < custom_redfield:
        ml_fix_n = ((start_po4 * custom_redfield) - start_no3) * tank_vol / c_n
        st.error(f"⚠️ **Низький Азот:** Додайте ще **{ml_fix_n:.1f} мл** N для балансу {custom_redfield}:1.")
    elif ratio_final > custom_redfield:
        ml_fix_p = ((start_no3 / custom_redfield) - start_po4) * tank_vol / c_p
        st.error(f"⚠️ **Низький Фосфор:** Додайте ще **{ml_fix_p:.1f} мл** P для балансу {custom_redfield}:1.")
    
    # Калій
    if start_k < k_min:
        st.warning(f"❗ **Дефіцит Калію ({start_k:.1f} < {k_min:.1f}):** Рослини можуть зупинити ріст, з'являться дірки.")
    elif start_k > gh * 2.5:
        st.warning(f"⚠️ **Надлишок Калію:** Ризик блокування Ca та Mg (радікуліт молодих листків).")

    # Дозування на період
    f_end = forecast[-1]
    ml_n_need = get_ml_dose(f_end["NO3"], target_no3, c_n, tank_vol)
    ml_p_need = get_ml_dose(f_end["PO4"], target_po4, c_p, tank_vol)
    ml_k_need = get_ml_dose(f_end["K"], target_k, c_k, tank_vol)

    st.info(f"""**📅 Дозування на {days} днів:**
* **N (Азот):** {ml_n_need/days:.1f} мл/день
* **P (Фосфор):** {ml_p_need/days:.1f} мл/день
* **K (Калій):** {ml_k_need/days:.1f} мл/день

**📦 Всього за період:** N:{ml_n_need:.1f} | P:{ml_p_need:.1f} | K:{ml_k_need:.1f} мл""")

with col_rep:
    st.subheader("📋 Звіт для копіювання")
    report = f"""--- AQUA REPORT V8.3 ---
[БАЗОВІ] Об'єм: {tank_vol}л | Підміна: {change_l}л
[ПАРАМЕТРИ] GH:{gh} | KH:{kh} | pH:{ph} | TDS:{after_tds:.0f}
[ТЕСТИ] NO3:{no3_now} | PO4:{po4_now} | K:{k_now} | CO2:{co2_val:.1f}
[МОДЕЛЬ] Redfield:{ratio_final:.1f}:1 | Стабільність:{stability:.2f}
[СПОЖИВАННЯ] N:{adj_daily_no3:.2f} | P:{adj_daily_po4:.2f} | K:{adj_daily_k:.2f} (мг/л/д)

[ПЛАН КОРЕКЦІЇ ({days} дн.)]
- N: {ml_n_need/days:.1f} мл/д (Разом: {ml_n_need:.1f})
- P: {ml_p_need/days:.1f} мл/д (Разом: {ml_p_need:.1f})
- K: {ml_k_need/days:.1f} мл/д (Разом: {ml_k_need:.1f})
-----------------------"""
    st.code(report, language="text")

# ---------------- STABILITY ENGINE ----------------

def stability_engine(no3, po4, k):
    # 1. нормальні діапазони (можеш змінити)
    no3_min, no3_max = 5, 25
    po4_min, po4_max = 0.2, 1.5
    k_min, k_max = 10, 30

    def score(x, low, high):
        if x < low:
            return x / low
        if x > high:
            return high / x
        return 1.0

    s_no3 = score(no3, no3_min, no3_max)
    s_po4 = score(po4, po4_min, po4_max)
    s_k = score(k, k_min, k_max)

    # Redfield як вторинний фактор
    ratio = no3 / po4 if po4 > 0 else 0
    redfield_score = 1 / (1 + abs((ratio - custom_redfield) / custom_redfield))

    # фінальна стабільність
    stability = (0.5 * s_no3 + 0.3 * s_po4 + 0.2 * s_k) * redfield_score

    return clamp(stability, 0.05, 1.0), ratio


stability, ratio_now = stability_engine(no3_now, po4_now, k_now)
