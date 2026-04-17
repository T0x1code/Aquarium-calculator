import streamlit as st

# 1. Налаштування
st.set_page_config(page_title="Wong Aquarium Dashboard")

st.title("🌿 Баланс Акваріума")
st.write("Методологія Денніса Вонга (Dennis Wong)")

# 2. Повзунки параметрів
no3 = st.sidebar.slider("NO3 (Нітрати)", 0.0, 50.0, 20.0, 0.5)
po4 = st.sidebar.slider("PO4 (Фосфати)", 0.0, 5.0, 1.0, 0.05)
k = st.sidebar.slider("K (Калій)", 0.0, 30.0, 9.0, 0.5)
gh = st.sidebar.slider("GH (Жорсткість)", 0, 20, 10, 1)
kh = st.sidebar.slider("KH (Лужність)", 0, 20, 4, 1)
ph = st.sidebar.slider("pH (Кислотність)", 5.5, 8.5, 6.0, 0.1)

# 3. Основні розрахунки
co2 = 3 * kh * (10**(7 - ph))
redfield = no3 / po4 if po4 > 0 else 0
k_target = gh * 1.5

# 4. Вивід результатів
st.header("📊 Поточні показники")
col1, col2, col3 = st.columns(3)
col1.metric("CO2 mg/l", round(co2, 1))
col2.metric("Пропорція NO3:PO4", round(redfield, 1))
col3.metric("K:GH Offset", round(k - gh, 1))

st.divider()

# 5. Аналіз Панелей
st.subheader("ПАНЕЛЬ А: Статус CO2")
if co2 > 45:
    st.error(f"Критичний надлишок! ({round(co2,1)} ppm). Ризик для риб.")
elif 20 <= co2 <= 35:
    st.success(f"Оптимально ({round(co2,1)} ppm).")
else:
    st.warning(f"Низький або нестабільний рівень ({round(co2,1)} ppm).")

st.subheader("ПАНЕЛЬ Б: Пропорція Редфілда")
if 15 <= redfield <= 22:
    st.success(f"Золота зона ({round(redfield,1)}). Баланс оптимальний.")
else:
    st.info(f"Поточне співвідношення: {round(redfield,1)}. Ідеал: 16-20.")

st.subheader("ПАНЕЛЬ В: Антагонізм (GH/K)")
if gh > 8 and k < k_target:
    st.error(f"БЛОКУВАННЯ! При GH {gh} Калій має бути не менше {round(k_target,1)} мг/л.")
else:
    st.success("Транспорт нутрієнтів у нормі.")
