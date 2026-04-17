import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V7.6", layout="wide")
st.title("🌿 Toxicode Aquarium System V7.6 Pro")

# ---------------- 1. SIDEBAR: НАЛАШТУВАННЯ ТА ЦІЛІ ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0)
    
    st.divider()
    st.subheader("🎯 Ваші цілі (Target)")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0)
    
    st.divider()
    st.subheader("⚙️ Налаштування аналітики")
    custom_redfield = st.slider("Бажана пропорція Редфілда (N:1P)", 5, 30, 15)
    co2_limit = st.slider("Поріг тривоги CO2 (мг/л)", 20, 50, 35)
    days = st.slider("Період прогнозу (днів)", 1, 14, 7)

# ---------------- 2. КАЛЬКУЛЯТОР СПОЖИВАННЯ ----------------
st.header("📉 1. Калькулятор реального споживання")
st.caption('Враховує підміни та внесені добрива за минулий період.')

with st.expander("Розгорнути для аналізу минулого періоду"):
    t1, t2, t3 = st.tabs(["Азот (NO3)", "Фосфор (PO4)", "Калій (K)"])
    
    def calc_real_cons(tab, name, key_p):
        with tab:
            c1, c2, c3 = st.columns(3)
            p_test = c1.number_input(f"Тест {name} (початок)", value=15.0, key=f"p_{key_p}")
            c_test = c2.number_input(f"Тест {name} (зараз)", value=10.0, key=f"c_{key_p}")
            added = c3.number_input(f"Внесено {name} за цей час", value=0.0, key=f"a_{key_p}")
            
            col_low1, col_low2 = st.columns(2)
            p_change = col_low1.slider(f"% підміни за цей час ({name})", 0, 100, 0, key=f"ch_{key_p}")
            d_pass = col_low2.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{key_p}")
            
            # Формула: (Початок - те що винесли підміною + додали) - кінець / дні
            start_after_wash = p_test * (1 - p_change/100)
            res = (start_after_wash + added - c_test) / d_pass
            st.info(f"**Реальне споживання {name}:** {max(res, 0):.2f} мг/л в день")

    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

st.divider()

# ---------------- 3. ПОТОЧНІ ПАРАМЕТРИ ----------------
st.header("📋 2. Поточний стан та ввід даних")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Сьогоднішні тести")
    no3 = st.number_input("Поточний NO3", value=10.0)
    po4 = st.number_input("Поточний PO4", value=0.5)
    k = st.number_input("Поточний K", value=10.0)
    base_tds = st.number_input("Поточний TDS", value=150.0)

with col2:
    st.subheader("Параметри води")
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=2)
    ph = st.number_input("pH", value=6.8)

with col3:
    st.subheader("Споживання (мг/л/день)")
    daily_no3 = st.number_input("Споживання NO3", value=2.0)
    daily_po4 = st.number_input("Споживання PO4", value=0.1)
    daily_k = st.number_input("Споживання K", value=1.0)

st.divider()

# ---------------- 4. ПІДМІНА ТА ДОЗУВАННЯ ----------------
c_act1, c_act2 = st.columns([1, 2])

with c_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри підміни", value=50.0)
    w_tds = st.number_input("TDS нової води", value=110.0)
    
    pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3 = no3 * (1 - pct) 
    after_po4 = po4 * (1 - pct)
    after_k = k * (1 - pct)
    after_tds = base_tds * (1 - pct) + (w_tds * pct)

with c_act2:
    st.header("🧪 Дозування")
    cd1, cd2, cd3 = st.columns(3)
    c_n = cd1.number_input("N розчин г/л", value=50.0)
    d_n = cd1.number_input("Внести N мл", value=0.0)
    c_p = cd2.number_input("P розчин г/л", value=5.0)
    d_p = cd2.number_input("Внести P мл", value=0.0)
    c_k = cd3.number_input("K розчин г/л", value=20.0)
    d_k = cd3.number_input("Внести K мл", value=0.0)

start_no3 = after_no3 + (d_n * c_n / tank_vol)
start_po4 = after_po4 + (d_p * c_p / tank_vol)
start_k = after_k + (d_k * c_k / tank_vol)

# ---------------- 5. ПРОГНОЗ ----------------
st.header("📈 3. Прогноз динаміки")
forecast = []
for d in range(days + 1):
    forecast.append({
        "День": d,
        "NO3": max(start_no3 - daily_no3 * d, 0),
        "PO4": max(start_po4 - daily_po4 * d, 0),
        "K": max(start_k - daily_k * d, 0)
    })
df_f = pd.DataFrame(forecast).set_index("День")
st.line_chart(df_f)

# ---------------- 6. АНАЛІТИКА ----------------
st.header("📊 4. Аналіз параметрів")
res1, res2, res3, res4 = st.columns(4)

co2 = 3 * kh * (10**(7 - ph))
ratio = start_no3 / start_po4 if start_po4 > 0 else 0
k_floor = gh * 1.5

# Візуалізація СО2
if co2 > co2_limit:
    res1.metric("CO2 (мг/л)", f"{co2:.1f}", "⚠️ НАДЛИШОК", delta_color="inverse")
    st.error(f"🔴 **УВАГА: Надлишок CO2 ({co2:.1f} мг/л)!** Це небезпечно для риб та креветок.")
else:
    res1.metric("CO2 (мг/л)", f"{co2:.1f}")

res2.metric("Редфілд (N:P)", f"{ratio:.1f}:1", f"Ціль {custom_redfield}:1", delta_color="off")
res3.metric("K:GH", f"{start_k:.1f}", f"Поріг {k_floor:.1f}", help="Це мінімальний рівень калію для засвоєння азоту при вашому GH.")
res4.metric("TDS прогноз", f"{after_tds:.0f}")

st.divider()

# ---------------- 7. ПІДСУМОК ----------------
st.header("📝 5. Діагноз та План")
f_no3 = df_f.iloc[-1]["NO3"]
f_po4 = df_f.iloc[-1]["PO4"]
f_k = df_f.iloc[-1]["K"]

def get_ml(curr, target, conc, vol):
    return ((target - curr) * vol) / conc if curr < target else 0

ml_n = get_ml(f_no3, target_no3, c_n, tank_vol)
ml_p = get_ml(f_po4, target_po4, c_p, tank_vol)
ml_k = get_ml(f_k, target_k, c_k, tank_vol)

col_l, col_r = st.columns([1.5, 1])

with col_l:
    st.subheader("Коригування доз")
    if ml_n > 0: st.warning(f"**N:** +{ml_n:.1f} мл на період (або {ml_n/days:.1f} мл/день)")
    if ml_p > 0: st.warning(f"**P:** +{ml_p:.1f} мл на період (або {ml_p/days:.1f} мл/день)")
    if ml_k > 0: st.warning(f"**K:** +{ml_k:.1f} мл на період (або {ml_k/days:.1f} мл/день)")
    if ml_n == 0 and ml_p == 0 and ml_k == 0: st.success("Запасів макроелементів достатньо!")

with col_r:
    st.subheader("💡 Висновок")
    if ratio < (custom_redfield - 5): st.error("⚠️ Ризик синьо-зелених (низький азот/високий фосфор).")
    elif ratio > (custom_redfield + 5): st.error("⚠️ Ризик ксенококусу (забагато азоту).")
    if start_k < k_floor: st.error("🚫 Калій нижче порогу блокування! Рослини не їдять нітрат.")
    if not any([ratio < (custom_redfield-5), ratio > (custom_redfield+5), start_k < k_floor]):
        st.success("🌟 Система збалансована під ваші цілі.")
