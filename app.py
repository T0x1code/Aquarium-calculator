import streamlit as st
import pandas as pd
import numpy as np
import json
import os

st.set_page_config(page_title="Toxicode V5 AI", layout="wide")
st.title("🧠 Toxicode Aquarium AI V5")

DATA_FILE = "aquarium_data.json"

# --- LOAD / SAVE ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"events": [], "k_factor": 1.0}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

# --- SESSION ---
if "events" not in st.session_state:
    st.session_state.events = data["events"]

if "k_factor" not in st.session_state:
    st.session_state.k_factor = data.get("k_factor", 1.0)

# --- UI ---
st.header("⚙️ Система")

tank_vol = st.number_input("Обʼєм (л)", 10.0, 1000.0, 50.0)
target_no3 = st.number_input("Ціль NO3", value=20.0)
target_po4 = st.number_input("Ціль PO4", value=1.0)

st.divider()

# --- EVENTS ---
st.header("➕ Подія")

event_type = st.selectbox("Тип", ["measurement","dosing","water_change"])
day = st.number_input("День", value=0)

if event_type == "measurement":
    no3 = st.number_input("NO3", value=20.0)
    po4 = st.number_input("PO4", value=1.0)

    if st.button("Додати"):
        st.session_state.events.append({"type":"measurement","day":day,"no3":no3,"po4":po4})
        save_data({"events":st.session_state.events,"k_factor":st.session_state.k_factor})

elif event_type == "dosing":
    add_no3 = st.number_input("NO3 додано", value=0.0)
    add_po4 = st.number_input("PO4 додано", value=0.0)

    if st.button("Додати"):
        st.session_state.events.append({"type":"dosing","day":day,"no3":add_no3,"po4":add_po4})
        save_data({"events":st.session_state.events,"k_factor":st.session_state.k_factor})

elif event_type == "water_change":
    pct = st.number_input("% підміни", value=30.0)

    if st.button("Додати"):
        st.session_state.events.append({"type":"water_change","day":day,"pct":pct/100})
        save_data({"events":st.session_state.events,"k_factor":st.session_state.k_factor})

st.divider()

# --- MODEL ---
st.header("🔬 Модель")

if st.session_state.events:
    events = sorted(st.session_state.events, key=lambda x: x["day"])

    no3 = None
    po4 = None
    history = []

    for e in events:
        if e["type"] == "measurement":
            no3 = e["no3"]
            po4 = e["po4"]

        elif e["type"] == "dosing" and no3 is not None:
            no3 += e["no3"]
            po4 += e["po4"]

        elif e["type"] == "water_change" and no3 is not None:
            no3 *= (1 - e["pct"])
            po4 *= (1 - e["pct"])

        history.append({"day": e["day"], "no3": no3, "po4": po4})

    df = pd.DataFrame(history).dropna()

    df["no3_smooth"] = df["no3"].rolling(3, min_periods=1).mean()
    df["po4_smooth"] = df["po4"].rolling(3, min_periods=1).mean()

    st.line_chart(df.set_index("day")[["no3_smooth","po4_smooth"]])

else:
    st.warning("Немає даних")

st.divider()

# --- LEARNING ---
st.header("🧠 Самонавчання")

if len(df) >= 3:
    df["d_no3"] = df["no3_smooth"].diff()
    df["d_day"] = df["day"].diff()

    observed = (-df["d_no3"]/df["d_day"]).dropna().mean()

    predicted = observed * st.session_state.k_factor

    error = observed - predicted

    # UPDATE FACTOR
    lr = 0.1
    st.session_state.k_factor += lr * (error / max(observed,0.1))

    st.metric("Observed NO3", f"{observed:.2f}")
    st.metric("k_factor", f"{st.session_state.k_factor:.2f}")

    save_data({"events":st.session_state.events,"k_factor":st.session_state.k_factor})

else:
    observed = 2.0
    st.info("Мало даних")

st.divider()

# --- FORECAST ---
st.header("📈 Прогноз")

days = st.slider("Днів",1,14,7)

if not df.empty:
    last = df.iloc[-1]

    cons = observed * st.session_state.k_factor

    forecast = pd.DataFrame({
        "day":range(days),
        "no3":[max(last["no3"]-cons*d,0) for d in range(days)],
        "po4":[max(last["po4"]-0.1*d,0) for d in range(days)]
    })

    st.line_chart(forecast.set_index("day"))

st.divider()

# --- ANOMALY ---
st.header("🚨 Аномалії")

if len(df) >= 3:
    z = (df["no3_smooth"] - df["no3_smooth"].mean()) / df["no3_smooth"].std()

    if any(abs(z) > 2):
        st.error("Аномалія в даних (можливо тест або помилка)")

st.divider()

# --- RECOMMEND ---
st.header("🤖 Рекомендації")

if not df.empty:
    last = df.iloc[-1]

    need_no3 = target_no3 - last["no3"]

    if need_no3 > 2:
        st.warning(f"Додати NO3: {need_no3:.1f}")
    elif need_no3 < -5:
        st.error("Передоз → зменш дозування")
    else:
        st.success("Баланс стабільний")
