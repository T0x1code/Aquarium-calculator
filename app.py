import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

st.set_page_config(page_title="Toxicode Predictive System", layout="wide")
st.title("🧠 Toxicode Predictive Aquarium Model")

DATA_FILE = "aquarium_data_v2.json"

# ---------------- LOAD / SAVE ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"events": [], "params": default_params()}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ---------------- DEFAULT PARAMS ----------------
def default_params():
    return {
        "Vmax_no3": 2.0,
        "K_no3": 5.0,
        "Vmax_po4": 0.2,
        "K_po4": 0.1,
        "biomass": 1.0,
        "light": 1.0,
        "co2": 1.0,
        "fish_no3": 0.3
    }

data = load_data()

# ---------------- SESSION ----------------
if "events" not in st.session_state:
    st.session_state.events = data["events"]

if "params" not in st.session_state:
    st.session_state.params = data["params"]

# ---------------- SYSTEM ----------------
st.header("⚙️ Параметри системи")

params = st.session_state.params

params["biomass"] = st.slider("Біомаса (0.5–3)", 0.5, 3.0, float(params["biomass"]))
params["light"] = st.slider("Світло (0.5–2)", 0.5, 2.0, float(params["light"]))
params["co2"] = st.slider("CO2 (0.5–2)", 0.5, 2.0, float(params["co2"]))
params["fish_no3"] = st.number_input("NO3 від риби (мг/л/день)", value=float(params["fish_no3"]))

st.divider()

# ---------------- EVENTS ----------------
st.header("➕ Подія")

event_type = st.selectbox("Тип", ["measurement","dosing","water_change"])
timestamp = datetime.now().isoformat()

if event_type == "measurement":
    no3 = st.number_input("NO3", value=10.0)
    po4 = st.number_input("PO4", value=0.5)
    k = st.number_input("K", value=10.0)

    if st.button("Додати вимір"):
        st.session_state.events.append({
            "type":"measurement",
            "time":timestamp,
            "no3":no3,
            "po4":po4,
            "k":k
        })
        save_data(st.session_state)

elif event_type == "dosing":
    no3 = st.number_input("NO3 додано", value=0.0)
    po4 = st.number_input("PO4 додано", value=0.0)
    k = st.number_input("K додано", value=0.0)

    if st.button("Додати дозування"):
        st.session_state.events.append({
            "type":"dosing",
            "time":timestamp,
            "no3":no3,
            "po4":po4,
            "k":k
        })
        save_data(st.session_state)

elif event_type == "water_change":
    pct = st.number_input("% підміни", value=30.0)

    if st.button("Додати підміну"):
        st.session_state.events.append({
            "type":"water_change",
            "time":timestamp,
            "pct":pct/100
        })
        save_data(st.session_state)

st.divider()

# ---------------- MODEL CORE ----------------
def step(state, dt_days, params):
    no3 = state["no3"]
    po4 = state["po4"]

    uptake_no3 = params["Vmax_no3"] * (no3 / (params["K_no3"] + no3))
    uptake_no3 *= params["light"] * params["co2"] * params["biomass"]

    uptake_po4 = params["Vmax_po4"] * (po4 / (params["K_po4"] + po4))
    uptake_po4 *= params["light"] * params["co2"] * params["biomass"]

    no3 = no3 + params["fish_no3"]*dt_days - uptake_no3*dt_days
    po4 = po4 - uptake_po4*dt_days

    return {
        "no3": max(no3,0),
        "po4": max(po4,0),
        "k": state["k"]
    }

# ---------------- SIMULATION ----------------
st.header("🔬 Модель")

if st.session_state.events:

    events = sorted(st.session_state.events, key=lambda x: x["time"])

    state = {"no3":None,"po4":None,"k":None}
    history = []

    last_time = None

    for e in events:
        t = datetime.fromisoformat(e["time"])

        if last_time and state["no3"] is not None:
            dt = (t - last_time).total_seconds()/86400
            state = step(state, dt, params)

        if e["type"] == "measurement":
            state["no3"] = e["no3"]
            state["po4"] = e["po4"]
            state["k"] = e["k"]

        elif e["type"] == "dosing":
            state["no3"] += e["no3"]
            state["po4"] += e["po4"]
            state["k"] += e["k"]

        elif e["type"] == "water_change":
            state["no3"] *= (1 - e["pct"])
            state["po4"] *= (1 - e["pct"])
            state["k"] *= (1 - e["pct"])

        history.append({
            "time":t,
            "no3":state["no3"],
            "po4":state["po4"]
        })

        last_time = t

    df = pd.DataFrame(history).dropna()

    st.line_chart(df.set_index("time"))

else:
    st.warning("Немає даних")

st.divider()

# ---------------- FORECAST ----------------
st.header("📈 Прогноз")

days = st.slider("Днів",1,14,7)

if not df.empty:

    state = {
        "no3":df.iloc[-1]["no3"],
        "po4":df.iloc[-1]["po4"],
        "k":0
    }

    forecast = []

    for d in range(days):
        state = step(state, 1, params)
        forecast.append({
            "day":d,
            "no3":state["no3"],
            "po4":state["po4"]
        })

    forecast_df = pd.DataFrame(forecast)

    st.line_chart(forecast_df.set_index("day"))

st.divider()

# ---------------- RECOMMEND ----------------
st.header("🤖 Рекомендації")

target_no3 = st.number_input("Ціль NO3", value=15.0)

if not df.empty:

    current = df.iloc[-1]["no3"]

    future = forecast_df.iloc[-1]["no3"]

    if future < target_no3:
        need = target_no3 - future
        st.warning(f"Рекомендовано додати NO3: {need:.1f} мг/л")
    else:
        st.success("Все стабільно")

st.divider()

# ---------------- SAVE PARAMS ----------------
save_data({
    "events": st.session_state.events,
    "params": st.session_state.params
})
