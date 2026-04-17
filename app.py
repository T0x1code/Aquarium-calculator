import streamlit as st

# 1. Базові налаштування
st.set_page_config(page_title="Wong Aquarium Dashboard", layout="wide")

# 2. Спрощений блок стилів (щоб не було помилок)
st.markdown("""
<style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; border: 1px solid #eee; }
    [data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_input_html=True)

st.title("🌿 Баланс Акваріума (Dennis Wong)")

# 3. Ввід даних у колонках
col1, col2, col3 = st.columns(3)

with col1:
    no3 = st.slider("NO3 (Нітрати)", 0.0, 50.0, 20.0, step=0.5)
    po4 = st.slider("PO4 (Фосфати)", 0.0, 5.0, 1.0, step=0.05)
with col2:
    k = st.slider("K (Калій)", 0.0, 30.0, 9.0, step=0.5)
    gh = st.slider("GH (Жорсткість)", 0, 20, 10)
with col3:
    kh = st.slider("KH (Лужність)", 0, 20, 4)
    ph = st.slider("pH (Кислотність)", 5.5, 8.5, 6.0, step=0.1)

# 4. Розрахунки
co2 = 3 * kh * (10**(7 - ph))
redfield = no3 / po4 if po4 > 0 else 0
k_target = gh * 1.5

# 5. Метрики зверху
m1, m2, m3 = st.columns(3)
m1.metric("NO3:PO4 RATIO", f"{redfield:.1f}")
m2.metric("K:GH OFFSET", f"{k - gh:.1f}")
m3.metric("CO2 mg/l", f"{co2:.1f}")

st.divider()

# 6. Панелі статусу
# ПАНЕЛЬ А: CO2
if co2 > 45:
    st.error(f"🔴 ПАНЕЛЬ А: Критичний надлишок CO2 ({co2:.1f} ppm). Ризик задухи!")
elif 20 <= co2 <= 35:
    st.success(f"🟢 ПАНЕЛЬ А: CO2 в нормі ({co2:.1f} ppm).")
else:
    st.warning(f"🟡 ПАНЕЛЬ А: Низький рівень CO2 ({co2:.1f} ppm).")

# ПАНЕЛЬ Б: РЕДФІЛД
if 15 <= redfield <= 22:
    st.success(f"✅ ПАНЕЛЬ Б: Пропорція Редфілда ({redfield:.1f}) — Оптимально.")
else:
    st.info(f"📊 ПАНЕЛЬ Б: Поточна пропорція — {redfield:.1f}.")

# ПАНЕЛЬ В: АНТАГОНІЗМ
if gh > 8 and k < k_target:
    st.error(f"🚫 ПАНЕЛЬ В: GH блокує нітрати. Підніміть K до {k_target:.1f} мг/л.")
else:
    st.success("💎 ПАНЕЛЬ В: Транспорт нутрієнтів у нормі.")
