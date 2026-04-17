import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V9.4", layout="wide")
st.title("Toxicode Aquarium System V9.4 — C:N:P:K + Full Control")

# ======================== HELPER FUNCTIONS ========================
def clamp(v, min_v, max_v):
    return max(min(v, max_v), min_v)

def calculate_co2(kh, ph):
    return 3 * kh * (10 ** (7 - ph))

def redfield_balance(no3, po4, target_ratio):
    if po4 <= 0:
        return "No P", 0
    ratio = no3 / po4
    if ratio < target_ratio * 0.8:
        return "N deficit", ratio
    elif ratio > target_ratio * 1.2:
        return "P deficit", ratio
    return "balance", ratio

def get_optimal_k_range(gh):
    return {
        'min': gh * 1.2,
        'opt_low': gh * 1.5,
        'opt_high': gh * 2.5,
        'max': gh * 3.0,
        'target': gh * 1.8
    }

def calculate_cnpk_status(carbon_estimate, no3, po4, k):
    if carbon_estimate > 0:
        c_ratio = carbon_estimate / po4 if po4 > 0 else 999
        c_status = "normal" if 200 < c_ratio < 600 else "C deficit" if c_ratio <= 200 else "C excess"
    else:
        c_status = "unknown"
    
    np_ratio = no3 / po4 if po4 > 0 else 999
    if np_ratio < 10:
        np_status = "N deficit"
    elif np_ratio > 22:
        np_status = "P deficit"
    else:
        np_status = "balance"
    
    kn_ratio = k / no3 if no3 > 0 else 999
    if kn_ratio < 0.3:
        k_status = "K deficit"
    elif kn_ratio > 1.5:
        k_status = "K excess"
    else:
        k_status = "balance"
    
    return {
        'c_status': c_status,
        'np_ratio': np_ratio,
        'np_status': np_status,
        'kn_ratio': kn_ratio,
        'k_status': k_status
    }

# ======================== SIDEBAR ========================
with st.sidebar:
    st.header("System Configuration")
    tank_vol = st.number_input("Net water volume (L)", value=200.0, step=1.0)
    
    st.divider()
    st.subheader("Target Values")
    target_no3 = st.number_input("Target NO3 (mg/L)", value=15.0, step=1.0)
    target_po4 = st.number_input("Target PO4 (mg/L)", value=1.0, step=0.1)
    target_k = st.number_input("Target K (mg/L)", value=15.0, step=1.0)
    target_tds = st.number_input("Target TDS", value=120.0, step=5.0)
    
    st.divider()
    st.subheader("Advanced Settings")
    custom_redfield = st.slider("Desired Redfield ratio (N:P)", 5, 30, 15)
    co2_min_opt = st.slider("Min CO2 (mg/L)", 0, 100, 25)
    co2_max_opt = st.slider("Max CO2 (mg/L)", 0, 100, 45)
    days = st.slider("Forecast period (days)", 1, 14, 7)

# ======================== 1. CONSUMPTION CALCULATOR ========================
st.header("1. Real Consumption Calculator")
consumption_results = {}

with st.expander("Past period analysis - enter two test results"):
    t1, t2, t3 = st.tabs(["NO3", "PO4", "K"])
    
    def calc_real_cons(tab, name, key_p):
        with tab:
            c1, c2, c3 = st.columns(3)
            p_test = c1.number_input(f"Test {name} (start)", value=15.0, step=0.1, key=f"p_{key_p}")
            c_test = c2.number_input(f"Test {name} (now)", value=10.0, step=0.1, key=f"c_{key_p}")
            added = c3.number_input(f"Added {name} (mg/L)", value=0.0, step=0.1, key=f"a_{key_p}")
            
            cl1, cl2 = st.columns(2)
            ch_l = cl1.number_input(f"Water change (L) for {name}", value=0.0, step=1.0, key=f"ch_l_{key_p}")
            days_between = cl2.number_input("Days between tests", value=7, min_value=1, key=f"d_{key_p}")
            
            pct_water_change = (ch_l / tank_vol) if tank_vol > 0 else 0
            res = (p_test * (1 - pct_water_change) + added - c_test) / days_between
            val = max(res, 0)
            consumption_results[name] = val
            st.info(f"Daily {name} consumption: {val:.2f} mg/L per day")
    
    calc_real_cons(t1, "NO3", "no3")
    calc_real_cons(t2, "PO4", "po4")
    calc_real_cons(t3, "K", "k")

# ======================== 2. CURRENT PARAMETERS ========================
st.header("2. Current Water Parameters")
col1, col2, col3 = st.columns(3)

with col1:
    no3_now = st.number_input("NO3 (mg/L)", value=10.0, step=1.0)
    po4_now = st.number_input("PO4 (mg/L)", value=0.5, step=0.1)
    k_now = st.number_input("K (mg/L)", value=10.0, step=1.0)
    base_tds = st.number_input("TDS", value=150.0, step=5.0)

with col2:
    gh = st.number_input("GH (dH)", value=6, step=1)
    kh = st.number_input("KH (dH)", value=2, step=1)
    ph = st.number_input("pH", value=6.8, step=0.1)

with col3:
    default_no3_cons = consumption_results.get('NO3', 2.0)
    default_po4_cons = consumption_results.get('PO4', 0.1)
    default_k_cons = consumption_results.get('K', 1.0)
    
    daily_no3 = st.number_input("NO3 consumption (mg/L/day)", value=default_no3_cons, step=0.1)
    daily_po4 = st.number_input("PO4 consumption (mg/L/day)", value=default_po4_cons, step=0.1)
    daily_k = st.number_input("K consumption (mg/L/day)", value=default_k_cons, step=0.1)

# ======================== 3. WATER CHANGE ========================
st.divider()
st.header("3. Water Change")
c_change, c_quality = st.columns(2)

with c_change:
    change_l = st.number_input("Water change volume (L)", value=50.0, step=1.0)
    pct = change_l / tank_vol if tank_vol > 0 else 0
    st.metric("Water change percent", f"{pct*100:.1f}%")

with c_quality:
    water_no3 = st.number_input("NO3 in new water (mg/L)", value=0.0, step=0.5)
    water_po4 = st.number_input("PO4 in new water (mg/L)", value=0.0, step=0.1)
    water_k = st.number_input("K in new water (mg/L)", value=0.0, step=1.0)
    water_tds = st.number_input("TDS of new water", value=110.0, step=5.0)

after_no3 = no3_now * (1 - pct) + water_no3 * pct
after_po4 = po4_now * (1 - pct) + water_po4 * pct
after_k = k_now * (1 - pct) + water_k * pct
after_tds = base_tds * (1 - pct) + water_tds * pct

# ======================== 4. FERTILIZER DOSING ========================
st.header("4. Fertilizer Dosing")
st.caption("Stock solution concentration (g/L) and current daily dose (mL/day)")

cd_n, cd_p, cd_k, cd_fe = st.columns(4)

with cd_n:
    conc_n = st.number_input("N (NO3) g/L", value=50.0, step=5.0, key="conc_n")
    current_dose_n_ml = st.number_input("Current N dose mL/day", value=0.0, step=1.0, key="dose_n")
    add_no3 = (current_dose_n_ml * conc_n) / tank_vol

with cd_p:
    conc_p = st.number_input("P (PO4) g/L", value=5.0, step=0.5, key="conc_p")
    current_dose_p_ml = st.number_input("Current P dose mL/day", value=0.0, step=0.5, key="dose_p")
    add_po4 = (current_dose_p_ml * conc_p) / tank_vol

with cd_k:
    conc_k = st.number_input("K g/L", value=20.0, step=2.0, key="conc_k")
    current_dose_k_ml = st.number_input("Current K dose mL/day", value=0.0, step=1.0, key="dose_k")
    add_k = (current_dose_k_ml * conc_k) / tank_vol

with cd_fe:
    conc_fe = st.number_input("Fe g/L", value=1.0, step=0.1, key="conc_fe")
    current_dose_fe_ml = st.number_input("Current Fe dose mL/day", value=0.0, step=0.5, key="dose_fe")
    add_fe = (current_dose_fe_ml * conc_fe) / tank_vol

final_no3 = after_no3 + add_no3
final_po4 = after_po4 + add_po4
final_k = after_k + add_k
final_tds = after_tds + (add_no3 + add_po4 + add_k + add_fe) * 0.5

# ======================== 5. STABILITY ========================
ratio_now = final_no3 / final_po4 if final_po4 > 0 else 0
stability = 1 / (1 + abs((ratio_now - custom_redfield) / custom_redfield))
st.caption(f"Stability coefficient (Redfield): {stability:.2f}")

# ======================== 6. FORECAST ========================
st.header(f"5. Dynamic forecast for {days} days")

forecast = []
curr_n, curr_p, curr_k = final_no3, final_po4, final_k

for d in range(days + 1):
    forecast.append({
        "Day": d,
        "NO3": round(curr_n, 1),
        "PO4": round(curr_p, 2),
        "K": round(curr_k, 1)
    })
    curr_n = clamp(curr_n + (current_dose_n_ml * conc_n / tank_vol) - (daily_no3 * stability), 0, 100)
    curr_p = clamp(curr_p + (current_dose_p_ml * conc_p / tank_vol) - (daily_po4 * stability), 0, 10)
    curr_k = clamp(curr_k + (current_dose_k_ml * conc_k / tank_vol) - (daily_k * stability), 0, 100)

df_forecast = pd.DataFrame(forecast).set_index("Day")
st.line_chart(df_forecast)

# ======================== 7. C:N:P:K ========================
st.header("6. C:N:P:K Ratio")

co2_val = calculate_co2(kh, ph)
cnpk_status = calculate_cnpk_status(co2_val, final_no3, final_po4, final_k)

col_c, col_n, col_p, col_k_bal = st.columns(4)

with col_c:
    st.metric("CO2 (C)", f"{co2_val:.1f} mg/L")
    if co2_val < co2_min_opt:
        st.caption("C deficit")
    elif co2_val > co2_max_opt:
        st.caption("C excess")
    else:
        st.caption("C normal")

with col_n:
    st.metric("NO3 (N)", f"{final_no3:.1f} mg/L")
    if cnpk_status['np_status'] == "N deficit":
        st.caption("N deficit")
    else:
        st.caption("N normal")

with col_p:
    st.metric("PO4 (P)", f"{final_po4:.2f} mg/L")
    if cnpk_status['np_status'] == "P deficit":
        st.caption("P deficit")
    else:
        st.caption("P normal" if final_po4 > 0.2 else "P low")

with col_k_bal:
    st.metric("K", f"{final_k:.1f} mg/L")
    if cnpk_status['k_status'] == "K deficit":
        st.caption("K deficit")
    elif cnpk_status['k_status'] == "K excess":
        st.caption("K excess")
    else:
        st.caption("K normal")

# ======================== 8. K/GH ========================
st.header("7. K/GH Ratio")

k_opt_range = get_optimal_k_range(gh)
k_gh_ratio = final_k / gh if gh > 0 else 0

with st.expander("How to calculate target K from GH", expanded=True):
    st.markdown(f"""
    ### Optimal potassium formula

    **For your GH = {gh} dH:**

    | Parameter | Formula | Value (mg/L K) |
    |-----------|---------|-----------------|
    | Minimum | GH x 1.2 | **{k_opt_range['min']:.1f}** |
    | Optimal (low) | GH x 1.5 | **{k_opt_range['opt_low']:.1f}** |
    | Optimal (target) | GH x 1.8 | **{k_opt_range['target']:.1f}** |
    | Optimal (high) | GH x 2.5 | **{k_opt_range['opt_high']:.1f}** |
    | Maximum | GH x 3.0 | **{k_opt_range['max']:.1f}** |

    > **Remember:** K_target (mg/L) = GH x 1.8
    >
    > Safe range: GH x 1.5 to GH x 2.5
    """)

col_k1, col_k2, col_k3 = st.columns(3)

with col_k1:
    st.metric("Current K", f"{final_k:.1f} mg/L")
    st.caption(f"GH = {gh} dH")

with col_k2:
    st.metric("K/GH ratio", f"{k_gh_ratio:.2f}")

with col_k3:
    if final_k < k_opt_range['min']:
        st.error("CRITICAL K DEFICIT")
        st.write(f"Need to raise by {k_opt_range['min'] - final_k:.1f} mg/L")
    elif final_k < k_opt_range['opt_low']:
        st.warning("Moderate K deficit")
        st.write(f"Raise to {k_opt_range['opt_low']:.0f}-{k_opt_range['opt_high']:.0f} mg/L")
    elif final_k <= k_opt_range['opt_high']:
        st.success("Optimal K")
    elif final_k <= k_opt_range['max']:
        st.warning("Beginning of K antagonism")
        st.write(f"Reduce K by {final_k - k_opt_range['opt_high']:.1f} mg/L")
    else:
        st.error("CRITICAL K OVERDOSE")
        st.write(f"Urgently reduce K by {final_k - k_opt_range['max']:.1f} mg/L")

# ======================== 9. CORRECTION PLAN (FIXED) ========================
st.divider()
st.header("8. Dose Correction Plan")

f_end = forecast[-1]

# Calculate required concentration change in mg/L
delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4 - f_end["PO4"]
delta_k = target_k - f_end["K"]

# Calculate required dose change in mL/day to reach target
# IMPORTANT: This calculates the DAILY dose needed to reach target
if delta_no3 > 0:
    # Need to raise - calculate additional daily dose
    required_n_ml_per_day = (delta_no3 * tank_vol) / (conc_n * days) if conc_n > 0 else 0
    new_dose_n = current_dose_n_ml + required_n_ml_per_day
    correction_text_n = f"+{required_n_ml_per_day:.1f} mL/day"
elif delta_no3 < 0:
    # Need to lower - calculate reduction in daily dose
    reduce_n_ml_per_day = (abs(delta_no3) * tank_vol) / (conc_n * days) if conc_n > 0 else 0
    new_dose_n = max(0, current_dose_n_ml - reduce_n_ml_per_day)
    correction_text_n = f"-{reduce_n_ml_per_day:.1f} mL/day"
else:
    new_dose_n = current_dose_n_ml
    correction_text_n = "No change"

if delta_po4 > 0:
    required_p_ml_per_day = (delta_po4 * tank_vol) / (conc_p * days) if conc_p > 0 else 0
    new_dose_p = current_dose_p_ml + required_p_ml_per_day
    correction_text_p = f"+{required_p_ml_per_day:.2f} mL/day"
elif delta_po4 < 0:
    reduce_p_ml_per_day = (abs(delta_po4) * tank_vol) / (conc_p * days) if conc_p > 0 else 0
    new_dose_p = max(0, current_dose_p_ml - reduce_p_ml_per_day)
    correction_text_p = f"-{reduce_p_ml_per_day:.2f} mL/day"
else:
    new_dose_p = current_dose_p_ml
    correction_text_p = "No change"

if delta_k > 0:
    required_k_ml_per_day = (delta_k * tank_vol) / (conc_k * days) if conc_k > 0 else 0
    new_dose_k = current_dose_k_ml + required_k_ml_per_day
    correction_text_k = f"+{required_k_ml_per_day:.1f} mL/day"
elif delta_k < 0:
    reduce_k_ml_per_day = (abs(delta_k) * tank_vol) / (conc_k * days) if conc_k > 0 else 0
    new_dose_k = max(0, current_dose_k_ml - reduce_k_ml_per_day)
    correction_text_k = f"-{reduce_k_ml_per_day:.1f} mL/day"
else:
    new_dose_k = current_dose_k_ml
    correction_text_k = "No change"

col_rec1, col_rec2, col_rec3 = st.columns(3)

with col_rec1:
    st.subheader("Nitrogen (N)")
    st.metric("Current dose", f"{current_dose_n_ml:.1f} mL/day")
    
    if delta_no3 > 0:
        st.warning(f"NO3 deficit: {delta_no3:.1f} mg/L after {days} days")
        st.info(f"Add {correction_text_n}")
    elif delta_no3 < 0:
        st.warning(f"NO3 excess: {abs(delta_no3):.1f} mg/L after {days} days")
        st.info(f"Reduce {correction_text_n}")
    else:
        st.success("NO3 target will be reached")
    
    st.metric("New recommended dose", f"{new_dose_n:.1f} mL/day")

with col_rec2:
    st.subheader("Phosphorus (P)")
    st.metric("Current dose", f"{current_dose_p_ml:.2f} mL/day")
    
    if delta_po4 > 0:
        st.warning(f"PO4 deficit: {delta_po4:.2f} mg/L after {days} days")
        st.info(f"Add {correction_text_p}")
    elif delta_po4 < 0:
        st.warning(f"PO4 excess: {abs(delta_po4):.2f} mg/L after {days} days")
        st.info(f"Reduce {correction_text_p}")
    else:
        st.success("PO4 target will be reached")
    
    st.metric("New recommended dose", f"{new_dose_p:.2f} mL/day")

with col_rec3:
    st.subheader("Potassium (K)")
    st.metric("Current dose", f"{current_dose_k_ml:.1f} mL/day")
    
    if delta_k > 0:
        st.warning(f"K deficit: {delta_k:.1f} mg/L after {days} days")
        st.info(f"Add {correction_text_k}")
    elif delta_k < 0:
        st.warning(f"K excess: {abs(delta_k):.1f} mg/L after {days} days")
        st.info(f"Reduce {correction_text_k}")
    else:
        st.success("K target will be reached")
    
    st.metric("New recommended dose", f"{new_dose_k:.1f} mL/day")

st.caption("How to read: Adjust your daily dose to the 'New recommended dose' value. Change gradually by 10-20% per day.")

# ======================== 10. EXPERT CONCLUSION ========================
st.header("9. Expert Conclusion")

redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
    st.subheader("System Status")

    if co2_val < co2_min_opt:
        st.warning(f"CO2: {co2_val:.1f} mg/L - deficit (norm {co2_min_opt}-{co2_max_opt})")
    elif co2_val > co2_max_opt:
        st.error(f"CO2: {co2_val:.1f} mg/L - excess (norm {co2_min_opt}-{co2_max_opt})")
    else:
        st.success(f"CO2: {co2_val:.1f} mg/L - normal")

    if redfield_status == "N deficit":
        st.warning(f"N:P = {redfield_ratio:.1f}:1 - nitrogen deficit (target {custom_redfield}:1)")
    elif redfield_status == "P deficit":
        st.warning(f"N:P = {redfield_ratio:.1f}:1 - phosphorus deficit (target {custom_redfield}:1)")
    else:
        st.success(f"N:P = {redfield_ratio:.1f}:1 - balance")

    if final_k < k_opt_range['opt_low']:
        st.warning(f"K/GH = {k_gh_ratio:.2f} - K deficit")
    elif final_k > k_opt_range['opt_high']:
        st.warning(f"K/GH = {k_gh_ratio:.2f} - K excess")
    else:
        st.success(f"K/GH = {k_gh_ratio:.2f} - normal")

with col_summary2:
    st.subheader(f"Forecast after {days} days")
    st.metric("NO3", f"{f_end['NO3']:.1f} mg/L", delta=f"{f_end['NO3'] - target_no3:.1f}")
    st.metric("PO4", f"{f_end['PO4']:.2f} mg/L", delta=f"{f_end['PO4'] - target_po4:.2f}")
    st.metric("K", f"{f_end['K']:.1f} mg/L", delta=f"{f_end['K'] - target_k:.1f}")

# ======================== 11. REPORT ========================
st.divider()
st.subheader("10. Report for Log")

report = f"""=== TOXICODE AQUARIUM V9.4 REPORT ===
Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

MAIN PARAMETERS
Volume: {tank_vol} L | Water change: {change_l} L ({pct*100:.1f}%)
GH: {gh} dH | KH: {kh} dH | pH: {ph} | TDS: {final_tds:.0f} (target {target_tds})
CO2: {co2_val:.1f} mg/L (norm {co2_min_opt}-{co2_max_opt})

MACRO
NO3: {final_no3:.1f} / {target_no3} mg/L
PO4: {final_po4:.2f} / {target_po4} mg/L
K:   {final_k:.1f} / {target_k} mg/L

C:N:P:K
N:P = {cnpk_status['np_ratio']:.1f}:1 -> {cnpk_status['np_status']}
K:N = {cnpk_status['kn_ratio']:.2f}:1 -> {cnpk_status['k_status']}

K/GH
K/GH = {k_gh_ratio:.2f} (norm 1.5-2.5)
Optimal K for GH={gh}: {k_opt_range['opt_low']:.0f}-{k_opt_range['opt_high']:.0f} mg/L

FORECAST AFTER {days} DAYS
NO3: {f_end['NO3']:.1f} mg/L
PO4: {f_end['PO4']:.2f} mg/L
K:   {f_end['K']:.1f} mg/L

DOSE CHANGE RECOMMENDATION
N: {current_dose_n_ml:.1f} -> {new_dose_n:.1f} mL/day ({correction_text_n})
P: {current_dose_p_ml:.2f} -> {new_dose_p:.2f} mL/day ({correction_text_p})
K: {current_dose_k_ml:.1f} -> {new_dose_k:.1f} mL/day ({correction_text_k})
====================================="""

st.code(report, language="text")

# ======================== 12. VALIDATION ========================
with st.expander("Validation & Safety"):
    st.markdown(f"""
    | Check | Current | Safe range | Status |
    |-------|---------|------------|--------|
    | NO3 | {final_no3:.1f} | 5-40 | {"OK" if 5 <= final_no3 <= 40 else "WARNING"} |
    | PO4 | {final_po4:.2f} | 0.2-2.5 | {"OK" if 0.2 <= final_po4 <= 2.5 else "WARNING"} |
    | CO2 | {co2_val:.1f} | {co2_min_opt}-{co2_max_opt} | {"OK" if co2_min_opt <= co2_val <= co2_max_opt else "WARNING"} |
    | K/GH | {k_gh_ratio:.2f} | 1.5-2.5 | {"OK" if 1.5 <= k_gh_ratio <= 2.5 else "WARNING"} |
    """)

    if final_no3 > 40:
        st.error("High NO3 - reduce N fertilizer")
    if final_po4 > 2.5:
        st.warning("High PO4 - algae risk")
    if co2_val > co2_max_opt:
        st.error("Reduce CO2 supply")
    if final_k > k_opt_range['max']:
        st.warning("K above maximum - risk of Ca/Mg blocking")

st.caption("Toxicode V9.4 | C:N:P:K Control | Smart dose correction")
