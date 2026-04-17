""")

# ======================== 9. ПЛАН КОРЕКЦІЇ (ПЕРЕРОБЛЕНИЙ) ========================
st.divider()
st.header("📅 6. План корекції дозування")

f_end = forecast[-1]

# Розраховуємо необхідну зміну КОНЦЕНТРАЦІЇ в мг/л
delta_no3 = target_no3 - f_end["NO3"]
delta_po4 = target_po4 - f_end["PO4"]
delta_k = target_k - f_end["K"]

# Переводимо в зміну дози (мл/день)
# Формула: зміна_мл = (зміна_мг_л × об'єм) / концентрація_добрива
change_n_ml = (delta_no3 * tank_vol) / conc_n if conc_n > 0 and delta_no3 > 0 else 0
change_p_ml = (delta_po4 * tank_vol) / conc_p if conc_p > 0 and delta_po4 > 0 else 0
change_k_ml = (delta_k * tank_vol) / conc_k if conc_k > 0 and delta_k > 0 else 0

# Для від'ємних змін (зменшення дози) — окрема логіка
reduce_n_ml = (abs(delta_no3) * tank_vol) / conc_n if conc_n > 0 and delta_no3 < 0 else 0
reduce_p_ml = (abs(delta_po4) * tank_vol) / conc_p if conc_p > 0 and delta_po4 < 0 else 0
reduce_k_ml = (abs(delta_k) * tank_vol) / conc_k if conc_k > 0 and delta_k < 0 else 0

# Нова рекомендована доза
new_dose_n = current_dose_n_ml + change_n_ml - reduce_n_ml
new_dose_p = current_dose_p_ml + change_p_ml - reduce_p_ml
new_dose_k = current_dose_k_ml + change_k_ml - reduce_k_ml

col_rec1, col_rec2, col_rec3 = st.columns(3)

with col_rec1:
st.subheader("🧪 Азот (N)")
st.metric("Поточна доза", f"{current_dose_n_ml:.1f} мл/день")

if delta_no3 > 0:
    st.warning(f"📈 **Дефіцит NO₃:** {delta_no3:.1f} мг/л")
    st.info(f"➕ **Додайте +{change_n_ml:.1f} мл/день**")
elif delta_no3 < 0:
    st.warning(f"📉 **Надлишок NO₃:** {abs(delta_no3):.1f} мг/л")
    st.info(f"➖ **Зменште на {reduce_n_ml:.1f} мл/день**")
else:
    st.success("✅ NO₃ в нормі")

st.metric("Нова рекомендована доза", f"{max(0, new_dose_n):.1f} мл/день")

with col_rec2:
st.subheader("💧 Фосфор (P)")
st.metric("Поточна доза", f"{current_dose_p_ml:.2f} мл/день")

if delta_po4 > 0:
    st.warning(f"📈 **Дефіцит PO₄:** {delta_po4:.2f} мг/л")
    st.info(f"➕ **Додайте +{change_p_ml:.2f} мл/день**")
elif delta_po4 < 0:
    st.warning(f"📉 **Надлишок PO₄:** {abs(delta_po4):.2f} мг/л")
    st.info(f"➖ **Зменште на {reduce_p_ml:.2f} мл/день**")
else:
    st.success("✅ PO₄ в нормі")

st.metric("Нова рекомендована доза", f"{max(0, new_dose_p):.2f} мл/день")

with col_rec3:
st.subheader("🌾 Калій (K)")
st.metric("Поточна доза", f"{current_dose_k_ml:.1f} мл/день")

if delta_k > 0:
    st.warning(f"📈 **Дефіцит K:** {delta_k:.1f} мг/л")
    st.info(f"➕ **Додайте +{change_k_ml:.1f} мл/день**")
elif delta_k < 0:
    st.warning(f"📉 **Надлишок K:** {abs(delta_k):.1f} мг/л")
    st.info(f"➖ **Зменште на {reduce_k_ml:.1f} мл/день**")
else:
    st.success("✅ K в нормі")

st.metric("Нова рекомендована доза", f"{max(0, new_dose_k):.1f} мл/день")

# Додаткова інформація
st.caption(f"""
💡 **Як читати рекомендації:**
- Якщо є **дефіцит** — додайте вказану кількість до поточної дози
- Якщо є **надлишок** — зменште поточну дозу на вказану кількість
- Змінюйте дозування **поступово**, не більше ніж на 20% за день
""")

# ======================== 10. ЕКСПЕРТНИЙ ВИСНОВОК ========================
st.header("📝 7. Експертний висновок")

co2_val = calculate_co2(kh, ph)
redfield_status, redfield_ratio = redfield_balance(final_no3, final_po4, custom_redfield)

col_summary1, col_summary2 = st.columns(2)

with col_summary1:
st.subheader("📊 Стан системи")

# CO₂
if co2_val < co2_min_opt:
    st.warning(f"💨 CO₂: {co2_val:.1f} мг/л — **дефіцит** (норма {co2_min_opt}–{co2_max_opt})")
elif co2_val > co2_max_opt:
    st.error(f"🐟 CO₂: {co2_val:.1f} мг/л — **надлишок** (норма {co2_min_opt}–{co2_max_opt})")
else:
    st.success(f"✅ CO₂: {co2_val:.1f} мг/л — норма")

# Redfield
if redfield_status == "дефіцит N":
    st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — **дефіцит азоту** (ціль {custom_redfield}:1)")
elif redfield_status == "дефіцит P":
    st.warning(f"⚠️ N:P = {redfield_ratio:.1f}:1 — **дефіцит фосфору** (ціль {custom_redfield}:1)")
else:
    st.success(f"✅ N:P = {redfield_ratio:.1f}:1 — баланс")

# K/GH
if final_k < k_opt_range['opt_low']:
    st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — **дефіцит K**")
elif final_k > k_opt_range['opt_high']:
    st.warning(f"⚠️ K/GH = {k_gh_ratio:.2f} — **надлишок K**")
else:
    st.success(f"✅ K/GH = {k_gh_ratio:.2f} — норма")

with col_summary2:
st.subheader("📋 Прогноз через {days} днів")
st.metric("NO₃", f"{f_end['NO3']:.1f} мг/л", delta=f"{f_end['NO3'] - target_no3:.1f}")
st.metric("PO₄", f"{f_end['PO4']:.2f} мг/л", delta=f"{f_end['PO4'] - target_po4:.2f}")
st.metric("K", f"{f_end['K']:.1f} мг/л", delta=f"{f_end['K'] - target_k:.1f}")

# ======================== 11. ЗВІТ ДЛЯ КОПІЮВАННЯ ========================
st.divider()
st.subheader("📋 8. Звіт для журналу")

report = f"""=== TOXICODE AQUARIUM V9.3 REPORT ===
📅 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

【ОСНОВНІ ПАРАМЕТРИ】
Об'єм: {tank_vol} л | Підміна: {change_l} л ({pct*100:.1f}%)
GH: {gh} °dH | KH: {kh} °dH | pH: {ph} | TDS: {final_tds:.0f} (ціль {target_tds})
CO₂: {co2_val:.1f} мг/л (норма {co2_min_opt}–{co2_max_opt})

【МАКРО】
NO3: {final_no3:.1f} / {target_no3} мг/л
PO4: {final_po4:.2f} / {target_po4} мг/л
K:   {final_k:.1f} / {target_k} мг/л

【C:N:P:K СПІВВІДНОШЕННЯ】
N:P = {cnpk_status['np_ratio']:.1f}:1 → {cnpk_status['np_status']}
K:N = {cnpk_status['kn_ratio']:.2f}:1 → {cnpk_status['k_status']}

【K/GH】
K/GH = {k_gh_ratio:.2f} (норма 1.5-2.5)
Оптимум K для GH={gh}: {k_opt_range['opt_low']:.0f}–{k_opt_range['opt_high']:.0f} мг/л

【ПРОГНОЗ ЧЕРЕЗ {days} ДНІВ】
NO3: {f_end['NO3']:.1f} мг/л
PO4: {f_end['PO4']:.2f} мг/л
K:   {f_end['K']:.1f} мг/л

【РЕКОМЕНДАЦІЯ ЗМІНИ ДОЗИ】
N: {current_dose_n_ml:.1f} → {max(0, new_dose_n):.1f} мл/день ({'+' if new_dose_n > current_dose_n_ml else ''}{new_dose_n - current_dose_n_ml:.1f})
P: {current_dose_p_ml:.2f} → {max(0, new_dose_p):.2f} мл/день ({'+' if new_dose_p > current_dose_p_ml else ''}{new_dose_p - current_dose_p_ml:.2f})
K: {current_dose_k_ml:.1f} → {max(0, new_dose_k):.1f} мл/день ({'+' if new_dose_k > current_dose_k_ml else ''}{new_dose_k - current_dose_k_ml:.1f})
====================================="""

st.code(report, language="text")

# ======================== 12. ВАЛІДАЦІЯ ========================
with st.expander("🛡️ Валідація та безпека"):
st.markdown(f"""
| Перевірка | Поточне | Безпечний діапазон | Статус |
|-----------|---------|--------------------|--------|
| **NO3** | {final_no3:.1f} | 5–40 | {"✅" if 5 <= final_no3 <= 40 else "⚠️"} |
| **PO4** | {final_po4:.2f} | 0.2–2.5 | {"✅" if 0.2 <= final_po4 <= 2.5 else "⚠️"} |
| **CO₂** | {co2_val:.1f} | {co2_min_opt}–{co2_max_opt} | {"✅" if co2_min_opt <= co2_val <= co2_max_opt else "⚠️"} |
| **K/GH** | {k_gh_ratio:.2f} | 1.5–2.5 | {"✅" if 1.5 <= k_gh_ratio <= 2.5 else "⚠️"} |
""")

if final_no3 > 40:
    st.error("🚨 Високий NO3 — зменште N добрива")
if final_po4 > 2.5:
    st.warning("⚠️ Високий PO4 — ризик водоростей")
if co2_val > co2_max_opt:
    st.error("🚨 Зменште подачу CO₂")
if final_k > k_opt_range['max']:
    st.warning("⚠️ K вище максимуму — ризик блокування Ca/Mg")

st.caption("⚡ Toxicode V9.3 | Повний контроль C:N:P:K | Динамічна корекція доз")
