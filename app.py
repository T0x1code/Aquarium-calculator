import streamlit as st

# 1. Налаштування сторінки
st.set_page_config(page_title="Toxicode Aquarium System", layout="wide")

st.title("🌿 Toxicode Aquarium System")
st.info("Універсальний калькулятор балансу (за методологією Dennis Wong)")

# --- 1. ЗАГАЛЬНІ ПАРАМЕТРИ АКВАРІУМА ---
st.header("📏 Загальні параметри")
tank_vol = st.number_input("Загальний об'єм води в акваріумі (нетто), л", value=50, step=1)

st.divider()

# --- 2. ПОТОЧНІ ТЕСТИ ТА ПІДМІНА ---
col_setup1, col_setup2 = st.columns([1, 2])

with col_setup1:
    st.subheader("📋 Поточні тести")
    base_no3 = st.number_input("Тест NO3, мг/л", value=20.0, step=0.5)
    base_po4 = st.number_input("Тест PO4, мг/л", value=1.0, step=0.05)
    base_k = st.number_input("Тест K, мг/л", value=10.0, step=0.5)
    gh = st.number_input("GH (Жорсткість)", value=8, step=1)
    kh = st.number_input("KH (Лужність)", value=3, step=1)
    ph = st.number_input("pH (Кислотність)", value=6.5, step=0.1)

with col_setup2:
    st.subheader("💧 Підміна води")
    change_liters = st.number_input("Скільки літрів води замінюється?", value=15.0, step=1.0)
    
    c_w1, c_w2 = st.columns(2)
    with c_w1:
        water_no3 = st.number_input("NO3 у новій воді, мг/л", value=0.0)
    with c_w2:
        water_po4 = st.number_input("PO4 у новій воді, мг/л", value=0.0)
    
    # Розрахунок відсотка та залишку
    change_pct = (change_liters / tank_vol) if tank_vol > 0 else 0
    after_w_no3 = (base_no3 * (1 - change_pct)) + (water_no3 * change_pct)
    after_w_po4 = (base_po4 * (1 - change_pct)) + (water_po4 * change_pct)
    
    st.write(f"📊 **Аналіз підміни:** Ви замінюєте **{change_pct*100:.1f}%** води.")
    st.write(f"📉 **Концентрація після підміни:** NO3: {after_w_no3:.1f} | PO4: {after_w_po4:.2f}")

st.divider()

# --- 3. ДОЗУВАННЯ ДОБРИВ ---
st.header("🧪 Дозування добрив")
st.caption("Вкажіть концентрацію вашого розчину (г/л) та дозу (мл)")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("### Азот (N)")
    conc_n = st.number_input("Концентрація NO3, г/л", value=50.0, key="c_n")
    dose_n = st.number_input("Доза N, мл", value=0.0, step=0.5, key="d_n")
    added_no3 = (dose_n * conc_n) / tank_vol

with c2:
    st.markdown("### Фосфор (P)")
    conc_p = st.number_input("Концентрація PO4, г/л", value=5.0, key="c_p")
    dose_p = st.number_input("Доза P, мл", value=0.0, step=0.5, key="d_p")
    added_po4 = (dose_p * conc_p) / tank_vol

with c3:
    st.markdown("### Калій (K)")
    conc_k = st.number_input("Концентрація K, г/л", value=20.0, key="c_k")
    dose_k = st.number_input("Доза K, мл", value=0.0, step=0.5, key="d_k")
    added_k = (dose_k * conc_k) / tank_vol

with c4:
    st.markdown("### Залізо (Fe)")
    conc_fe = st.number_input("Концентрація Fe, г/л", value=1.0, key="c_fe")
    dose_fe = st.number_input("Доза Fe, мл", value=0.0, step=0.5, key="d_fe")
    added_fe = (dose_fe * conc_fe) / tank_vol

# --- 4. ПІДСУМКИ ---
total_no3 = after_w_no3 + added_no3
total_po4 = after_w_po4 + added_po4
total_k = base_k + added_k
co2 = 3 * kh * (10**(7 - ph))
redfield = total_no3 / total_po4 if total_po4 > 0 else 0
k_target = gh * 1.5

st.divider()

# --- 5. ВІЗУАЛІЗАЦІЯ РЕЗУЛЬТАТІВ ---
st.header("📊 Прогноз стану системи")

res1, res2, res3, res4 = st.columns(4)
res1.metric("Фінальний NO3", f"{total_no3:.1f}", f"{total_no3 - base_no3:.1f} від старту")
res2.metric("Фінальний PO4", f"{total_po4:.2f}", f"{total_po4 - base_po4:.2f} від старту")
res3.metric("K:GH Offset", f"{total_k - gh:.1f}", f"+{added_k:.1f} K")
res4.metric("CO2 мг/л", f"{co2:.1f}")

st.subheader("Аналіз Toxicode")

# Аналіз CO2
if co2 > 40:
    st.error(f"🔴 **CO2:** Занадто високий ({co2:.1f} ppm). Ризик для фауни.")
elif 15 <= co2 <= 35:
    st.success(f"🟢 **CO2:** В ідеальній зоні ({co2:.1f} ppm).")
else:
    st.warning(f"🟡 **CO2:** Низький або нестабільний рівень ({co2:.1f} ppm).")

# Аналіз Редфілда
if 15 <= redfield <= 22:
    st.success(f"✅ **Редфілд:** {redfield:.1f} — Баланс NO3/PO4 дотримано.")
else:
    st.info(f"📊 **Редфілд:** {redfield:.1f}. Оптимально: 16-20.")

# Аналіз Калію
is_blocked = gh > 8 and total_k < k_target
if is_blocked:
    st.error(f"🚫 **K/GH:** Ризик блокування азоту. Підніміть K до {k_target:.1f} мг/л.")
else:
    st.success("💎 **K/GH:** Транспорт нутрієнтів у нормі.")

if added_fe > 0:
    st.info(f"🧬 Додано заліза: {added_fe:.2f} мг/л.")
