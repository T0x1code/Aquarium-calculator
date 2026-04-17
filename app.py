import streamlit as st

st.set_page_config(page_title="Wong Dashboard + Dosing", layout="wide")

st.title("🌿 Pro Aquarium Dashboard & Dosing")

# --- SIDEBAR: ПАРАМЕТРИ ТА ТЕСТИ ---
st.sidebar.header("1. Поточні тести води")
tank_volume = st.sidebar.number_input("Об'єм акваріума (нетто), л", value=50)

st.sidebar.markdown("---")
base_no3 = st.sidebar.slider("Тест NO3 (мг/л)", 0.0, 50.0, 10.0, 0.5)
base_po4 = st.sidebar.slider("Тест PO4 (мг/л)", 0.0, 5.0, 0.5, 0.05)
k = st.sidebar.slider("Тест K (мг/л)", 0.0, 30.0, 10.0, 0.5)
gh = st.sidebar.slider("GH (загальна)", 0, 20, 8, 1)
kh = st.sidebar.slider("KH (карбонатна)", 0, 20, 3, 1)
ph = st.sidebar.slider("pH (кислотність)", 5.5, 8.5, 6.5, 0.1)

# --- ОСНОВНА ПАНЕЛЬ: КАЛЬКУЛЯТОР ДОБРИВ ---
st.header("🧪 Калькулятор самомісів")
with st.expander("Налаштувати внесення добрив"):
    col_dose1, col_dose2 = st.columns(2)
    
    with col_dose1:
        st.subheader("Макро (Азот/Фосфор)")
        dose_ml = st.number_input("Скільки мл вносиш?", value=0.0, step=0.5)
        sol_no3_mg_ml = st.number_input("Концентрація NO3 у добриві (мг/мл)", value=10.0)
        sol_po4_mg_ml = st.number_input("Концентрація PO4 у добриві (мг/мл)", value=1.0)
    
    with col_dose2:
        st.info("💡 Порада: Якщо твій рецепт каже, що 100г солі на 1л дає 50 мг/мл NO3, впиши це сюди.")

# Розрахунок підняття концентрації
added_no3 = (dose_ml * sol_no3_mg_ml) / tank_volume
added_po4 = (dose_ml * sol_po4_mg_ml) / tank_volume

# Підсумкові значення для дашборду
total_no3 = base_no3 + added_no3
total_po4 = base_po4 + added_po4

# --- ЛОГІКА ДАШБОРДУ (Вонг) ---
co2 = 3 * kh * (10**(7 - ph))
redfield = total_no3 / total_po4 if total_po4 > 0 else 0
k_target = gh * 1.5

# --- ВІЗУАЛІЗАЦІЯ ---
st.divider()
st.subheader("📊 Результат після внесення добрив")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Підсумковий NO3", f"{total_no3:.1f}", f"+{added_no3:.1f}")
m2.metric("Підсумковий PO4", f"{total_po4:.2f}", f"+{added_po4:.2f}")
m3.metric("CO2 mg/l", f"{co2:.1f}")
m4.metric("Redfield Ratio", f"{redfield:.1f}")

# Панелі статусу
st.markdown("---")
c1, c2 = st.columns(2)

with c1:
    if 15 <= redfield <= 22:
        st.success(f"💎 Редфілд: {redfield:.1f} (Ідеально)")
    else:
        st.warning(f"⚠️ Редфілд: {redfield:.1f} (Дисбаланс)")

with c2:
    if gh > 8 and k < k_target:
        st.error(f"🚫 K:GH: Блокування! Треба K > {k_target:.1f}")
    else:
        st.success("✅ K:GH: Транспорт у нормі")

if co2 > 35:
    st.error(f"💀 CO2 занадто високий: {co2:.1f} ppm!")
