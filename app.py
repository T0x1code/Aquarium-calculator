"""
Toxicode Aquarium System V12
Архітектура: журнал подій → автоматичний розрахунок балансу.
Кожен розділ незалежний. Порядок вводу не має значення.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Toxicode Aquarium V12", layout="wide")
st.title("🌿 Toxicode Aquarium System V12")
st.caption("Журнал подій · Реальний баланс · Діагностика акваріума")

# ================================================================
# ІНІЦІАЛІЗАЦІЯ СТАНУ
# ================================================================
defaults = {
    'journal': [],       # список подій: тест, підміна, добриво
    'alerts': [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================================================================
# ДОПОМІЖНІ ФУНКЦІЇ
# ================================================================
def clamp(v, lo, hi):
    return max(lo, min(v, hi))

def calculate_co2(kh, ph):
    try:
        return round(3 * kh * (10 ** (7 - ph)), 2)
    except (ValueError, OverflowError):
        return 0.0

def get_k_range(gh):
    return {'min': gh*1.2, 'opt_low': gh*1.5, 'opt_high': gh*2.5, 'max': gh*3.0}

def algae_risk(no3, po4):
    if po4 <= 0:
        return "Немає даних"
    r = no3 / po4
    if r < 8:   return "🔴 Високий — дефіцит N → ціанобактерії"
    if r > 25:  return "🟠 Високий — дефіцит P → зелені водорості"
    if no3 > 30 or po4 > 1.5: return "🟡 Середній — надлишок макро"
    if no3 < 3  or po4 < 0.2: return "🟡 Середній — дефіцит макро"
    return "🟢 Низький"

def light_rec(co2, no3, po4):
    if co2 < 20 or no3 < 5 or po4 < 0.2:
        return "💡 Низьке (50-70%, 6-8 год)"
    if co2 > 30 and no3 > 10 and po4 > 0.5:
        return "⚡ Високе (90-100%, 10-12 год)"
    return "🌿 Середнє (70-90%, 8-10 год)"

def add_event(event: dict):
    st.session_state.journal.append({
        'id': len(st.session_state.journal),
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        **event
    })

def get_tests():
    return [e for e in st.session_state.journal if e['type'] == 'test']

def get_last_test():
    tests = get_tests()
    return tests[-1] if tests else None

# ================================================================
# РОЗРАХУНОК БАЛАНСУ між двома тестами
# ================================================================
def compute_balance(t_prev: dict, t_curr: dict, tank_vol: float):
    """
    Між двома тестами розраховує:
      - net_change: фактична зміна концентрації
      - wc_effect:  ефект підмін (зниження)
      - fert_added: внесено добрив (зростання)
      - organic:    накопичення з органіки/нітрифікації (якщо позитивне)
      - consumption: чисте споживання рослинами (якщо від'ємне)
    """
    dt_start = datetime.strptime(t_prev['created_at'], '%Y-%m-%d %H:%M:%S')
    dt_end   = datetime.strptime(t_curr['created_at'], '%Y-%m-%d %H:%M:%S')
    dt_days  = max((dt_end - dt_start).total_seconds() / 86400, 0.01)

    results = {}
    for param in ['no3', 'po4', 'k']:
        v_start = t_prev.get(param, 0)
        v_end   = t_curr.get(param, 0)

        # Збираємо всі події між тестами
        wc_total_frac = 0.0   # сумарна частка підмін
        fert_added    = 0.0   # сумарно внесено мг/л

        for ev in st.session_state.journal:
            ev_time = datetime.strptime(ev['created_at'], '%Y-%m-%d %H:%M:%S')
            if not (dt_start < ev_time <= dt_end):
                continue
            if ev['type'] == 'water_change':
                wc_frac = ev.get('volume_l', 0) / tank_vol if tank_vol > 0 else 0
                wc_total_frac += wc_frac
            elif ev['type'] == 'fertilizer':
                key = f'{param}_mgl'
                fert_added += ev.get(key, 0)

        # Ефект підміни: знижує концентрацію пропорційно
        # (спрощена модель: одна підміна; якщо кілька — накопичувальний ефект)
        wc_effect = v_start * min(wc_total_frac, 1.0)

        # Очікуване значення без споживання/накопичення
        expected = v_start - wc_effect + fert_added

        # Різниця між реальним і очікуваним — «невидима» зміна
        invisible = v_end - expected

        # invisible > 0 → накопичення (органіка, нітрифікація, блокування)
        # invisible < 0 → споживання рослинами (або інше видалення)
        net_change   = v_end - v_start
        consumption_per_day  = max(0, -invisible) / dt_days
        organic_per_day      = max(0,  invisible) / dt_days

        results[param] = {
            'v_start':     round(v_start, 3),
            'v_end':       round(v_end, 3),
            'net_change':  round(net_change, 3),
            'wc_effect':   round(wc_effect, 3),
            'fert_added':  round(fert_added, 3),
            'invisible':   round(invisible, 3),
            'consumption_per_day': round(consumption_per_day, 3),
            'organic_per_day':     round(organic_per_day, 3),
            'dt_days':     round(dt_days, 2),
        }
    return results

# ================================================================
# ПРОГНОЗ
# ================================================================
def run_forecast(start_vals: dict, cons: dict, organic: dict,
                 daily_fert: dict, wc_pct_per_day: float, n_days: int):
    rows = []
    v = {p: start_vals.get(p, 0) for p in ['no3','po4','k']}
    for d in range(n_days + 1):
        rows.append({'День': d,
                     'NO3': round(v['no3'], 2),
                     'PO4': round(v['po4'], 3),
                     'K':   round(v['k'],   2)})
        for p in ['no3','po4','k']:
            v[p] = clamp(
                v[p] * (1 - wc_pct_per_day)
                + daily_fert.get(p, 0)
                - cons.get(p, 0)
                + organic.get(p, 0),
                0, 500
            )
    return rows

# ================================================================
# SIDEBAR — глобальні налаштування
# ================================================================
with st.sidebar:
    st.header("⚙️ Налаштування акваріума")
    tank_vol    = st.number_input("Об'єм води (л)", value=200.0, step=5.0, min_value=1.0)
    gh          = st.number_input("GH (°dH)", value=6, step=1, min_value=0)
    kh          = st.number_input("KH (°dH)", value=2, step=1, min_value=0)

    st.divider()
    st.subheader("🎯 Цілі")
    target_no3  = st.number_input("Ціль NO3 (мг/л)", value=15.0, step=1.0)
    target_po4  = st.number_input("Ціль PO4 (мг/л)", value=1.0,  step=0.1)
    target_k    = st.number_input("Ціль K (мг/л)",   value=15.0, step=1.0)

    st.divider()
    st.subheader("🔬 Додатково")
    redfield    = st.slider("N:P ціль (Редфілд)", 5, 30, 15)
    co2_lo      = st.slider("CO₂ мін (мг/л)", 0, 60, 20)
    co2_hi      = st.slider("CO₂ макс (мг/л)", 0, 100, 40)
    forecast_days = st.slider("Прогноз (днів)", 1, 30, 7)

    po4_unit = st.radio("Тест PO4 показує:", ["PO4 (фосфат)", "P (фосфор)"], horizontal=True)
    po4_factor = 3.07 if po4_unit == "P (фосфор)" else 1.0
    if po4_factor != 1.0:
        st.caption("⚠️ P × 3.07 = PO4 — перерахунок автоматичний")

# ================================================================
# БЛОК A — ЖУРНАЛ ПОДІЙ
# ================================================================
st.header("📓 A. Журнал подій")
st.caption("Вводьте події в будь-якому порядку. Програма сама розрахує баланс.")

tab_test, tab_wc, tab_fert = st.tabs(["🧪 Тест води", "💧 Підміна води", "🌱 Внесення добрив"])

# --- Тест води ---
with tab_test:
    st.markdown("Введіть результати тесту. Час фіксується автоматично.")
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        t_no3 = st.number_input("NO3 (мг/л)", value=10.0, step=0.5, format="%.1f", key="t_no3")
        if po4_factor != 1.0:
            t_po4_raw = st.number_input("P (мг/л)", value=0.3, step=0.05, format="%.2f", key="t_po4")
            t_po4 = round(t_po4_raw * po4_factor, 3)
            st.caption(f"PO4 = {t_po4:.2f} мг/л")
        else:
            t_po4 = st.number_input("PO4 (мг/л)", value=0.5, step=0.05, format="%.2f", key="t_po4")
        t_k = st.number_input("K (мг/л)", value=10.0, step=0.5, format="%.1f", key="t_k")
    with tc2:
        t_ph_m = st.number_input("pH ранок (до CO₂)", value=7.2, step=0.1, format="%.1f", key="t_phm")
        t_ph_e = st.number_input("pH вечір (з CO₂)",  value=6.8, step=0.1, format="%.1f", key="t_phe")
        t_tds  = st.number_input("TDS", value=150.0, step=5.0, format="%.0f", key="t_tds")
        t_co2  = calculate_co2(kh, t_ph_e)
        st.metric("CO₂", f"{t_co2:.1f} мг/л")
    with tc3:
        t_note = st.text_area("Нотатка (необов'язково)",
                              placeholder="Наприклад: після підміни, рослини виглядають добре...",
                              key="t_note", height=100)
        # Ручне введення часу тесту
        t_manual_time = st.checkbox("Вказати час вручну", key="t_manual_time")
        if t_manual_time:
            t_date = st.date_input("Дата тесту", value=datetime.now().date(), key="t_date")
            t_time = st.time_input("Час тесту", value=datetime.now().time(), key="t_time")
            t_datetime_str = f"{t_date} {t_time}"
        else:
            t_datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if st.button("✅ Зберегти тест", type="primary", key="save_test"):
        ev = {
            'type': 'test',
            'no3': t_no3, 'po4': t_po4, 'k': t_k,
            'ph_morning': t_ph_m, 'ph_evening': t_ph_e,
            'tds': t_tds, 'co2': t_co2, 'note': t_note,
        }
        ev['created_at'] = t_datetime_str
        add_event(ev)
        st.success(f"✅ Тест збережено ({t_datetime_str})")
        st.rerun()

# --- Підміна води ---
with tab_wc:
    wc1, wc2 = st.columns(2)
    with wc1:
        wc_vol = st.number_input("Об'єм підміни (л)", value=50.0, step=5.0, key="wc_vol")
        wc_pct = wc_vol / tank_vol * 100 if tank_vol > 0 else 0
        st.metric("% підміни", f"{wc_pct:.1f}%")
        wc_note = st.text_input("Нотатка", key="wc_note",
                                placeholder="Наприклад: планова тижнева підміна")
    with wc2:
        st.markdown("**Параметри свіжої води (після ремінералізації):**")
        wc_no3_fresh = st.number_input("NO3 свіжої (мг/л)", value=0.0, step=0.5, key="wc_no3")
        wc_po4_fresh = st.number_input("PO4 свіжої (мг/л)", value=0.0, step=0.05, key="wc_po4")
        wc_k_fresh   = st.number_input("K свіжої (мг/л)",   value=0.0, step=0.5,  key="wc_k")
        st.caption("Якщо осмос — залишайте 0. Якщо кранова вода — введіть реальні значення.")

    wc_manual_time = st.checkbox("Вказати час вручну", key="wc_manual_time")
    if wc_manual_time:
        wc_date = st.date_input("Дата", value=datetime.now().date(), key="wc_date")
        wc_time_val = st.time_input("Час", value=datetime.now().time(), key="wc_time")
        wc_datetime_str = f"{wc_date} {wc_time_val}"
    else:
        wc_datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if st.button("✅ Зберегти підміну", type="primary", key="save_wc"):
        ev = {
            'type': 'water_change',
            'volume_l': wc_vol,
            'no3_fresh': wc_no3_fresh,
            'po4_fresh': wc_po4_fresh,
            'k_fresh':   wc_k_fresh,
            'note': wc_note,
        }
        ev['created_at'] = wc_datetime_str
        add_event(ev)
        st.success(f"✅ Підміну збережено: {wc_vol:.0f} л ({wc_pct:.1f}%)")
        st.rerun()

# --- Внесення добрив ---
with tab_fert:
    st.caption("Вказуйте концентрацію розчину і об'єм — програма сама перерахує мг/л в акваріумі.")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown("**Азот (NO3)**")
        f_n_ml   = st.number_input("N: мл розчину", value=0.0, step=1.0, key="f_n_ml")
        f_n_conc = st.number_input("N: г/л розчину", value=50.0, step=5.0, key="f_n_conc")
        f_n_mgl  = round(f_n_ml * f_n_conc / tank_vol, 3) if tank_vol > 0 else 0
        st.caption(f"→ +{f_n_mgl:.2f} мг/л NO3 в акваріумі")
    with fc2:
        st.markdown("**Фосфор (PO4)**")
        f_p_ml   = st.number_input("P: мл розчину", value=0.0, step=0.5, key="f_p_ml")
        f_p_conc = st.number_input("P: г/л розчину", value=5.0, step=0.5, key="f_p_conc")
        f_p_mgl  = round(f_p_ml * f_p_conc / tank_vol, 3) if tank_vol > 0 else 0
        st.caption(f"→ +{f_p_mgl:.3f} мг/л PO4 в акваріумі")
    with fc3:
        st.markdown("**Калій (K)**")
        f_k_ml   = st.number_input("K: мл розчину", value=0.0, step=1.0, key="f_k_ml")
        f_k_conc = st.number_input("K: г/л розчину", value=20.0, step=2.0, key="f_k_conc")
        f_k_mgl  = round(f_k_ml * f_k_conc / tank_vol, 3) if tank_vol > 0 else 0
        st.caption(f"→ +{f_k_mgl:.2f} мг/л K в акваріумі")

    f_note = st.text_input("Нотатка", key="f_note",
                           placeholder="Наприклад: щоденна доза EI, після підміни...")
    f_manual_time = st.checkbox("Вказати час вручну", key="f_manual_time")
    if f_manual_time:
        f_date = st.date_input("Дата", value=datetime.now().date(), key="f_date")
        f_time_val = st.time_input("Час", value=datetime.now().time(), key="f_time")
        f_datetime_str = f"{f_date} {f_time_val}"
    else:
        f_datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if st.button("✅ Зберегти внесення", type="primary", key="save_fert"):
        ev = {
            'type': 'fertilizer',
            'no3_mgl': f_n_mgl,
            'po4_mgl': f_p_mgl,
            'k_mgl':   f_k_mgl,
            'note': f_note,
        }
        ev['created_at'] = f_datetime_str
        add_event(ev)
        st.success(f"✅ Внесення збережено: NO3 +{f_n_mgl:.2f} / PO4 +{f_p_mgl:.3f} / K +{f_k_mgl:.2f} мг/л")
        st.rerun()

# Показати журнал
with st.expander("📋 Показати журнал подій"):
    if st.session_state.journal:
        df_j = pd.DataFrame(st.session_state.journal)
        type_labels = {'test': '🧪 Тест', 'water_change': '💧 Підміна', 'fertilizer': '🌱 Добриво'}
        df_j['Тип'] = df_j['type'].map(type_labels)
        show_cols = ['created_at', 'Тип', 'note']
        for c in ['no3','po4','k','volume_l','no3_mgl','po4_mgl','k_mgl']:
            if c in df_j.columns:
                show_cols.append(c)
        st.dataframe(df_j[[c for c in show_cols if c in df_j.columns]],
                     use_container_width=True)
        if st.button("🗑️ Очистити журнал", key="clear_journal"):
            st.session_state.journal = []
            st.rerun()
    else:
        st.info("Журнал порожній. Введіть перший тест вище ☝️")

# ================================================================
# БЛОК B — ПОТОЧНИЙ СТАН
# ================================================================
st.divider()
st.header("📋 B. Поточний стан")

last_test = get_last_test()
tests = get_tests()

if last_test:
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("NO3", f"{last_test['no3']:.1f} мг/л",
              delta=f"ціль {target_no3}" if last_test['no3'] != target_no3 else "✅ в цілі")
    b2.metric("PO4", f"{last_test['po4']:.2f} мг/л",
              delta=f"ціль {target_po4}" if last_test['po4'] != target_po4 else "✅ в цілі")
    b3.metric("K",   f"{last_test['k']:.1f} мг/л",
              delta=f"ціль {target_k}" if last_test['k'] != target_k else "✅ в цілі")
    b4.metric("CO₂", f"{last_test['co2']:.1f} мг/л",
              delta=f"норма {co2_lo}-{co2_hi}")
    st.caption(f"Останній тест: {last_test['created_at']}  |  {last_test.get('note','')}")
else:
    st.info("👆 Введіть перший тест у блоці А щоб побачити поточний стан.")

# ================================================================
# БЛОК C — АНАЛІЗ БАЛАНСУ (головна нова логіка)
# ================================================================
st.divider()
st.header("⚖️ C. Аналіз балансу між тестами")

if len(tests) >= 2:
    # Вибір пари тестів для аналізу
    test_labels = [f"{t['created_at']}  NO3={t['no3']} PO4={t['po4']} K={t['k']}" for t in tests]
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        idx_prev = st.selectbox("Початковий тест:", range(len(tests)-1),
                                format_func=lambda i: test_labels[i], key="bal_prev")
    with col_sel2:
        idx_curr = st.selectbox("Кінцевий тест:", range(1, len(tests)),
                                format_func=lambda i: test_labels[i],
                                index=len(tests)-2, key="bal_curr")

    if idx_curr <= idx_prev:
        st.warning("⚠️ Кінцевий тест має бути пізніше за початковий.")
    else:
        bal = compute_balance(tests[idx_prev], tests[idx_curr], tank_vol)

        for param, label, unit in [('no3','NO3','мг/л'), ('po4','PO4','мг/л'), ('k','K','мг/л')]:
            b = bal[param]
            with st.expander(f"**{label}**: {b['v_start']} → {b['v_end']} мг/л  "
                             f"({b['dt_days']:.1f} днів)", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ефект підміни", f"−{b['wc_effect']:.2f} мг/л",
                          help="Скільки вийшло з водою при підміні")
                c2.metric("Внесено добрив", f"+{b['fert_added']:.2f} мг/л",
                          help="Сумарно внесено добривами між тестами")
                c3.metric("Споживання рослинами",
                          f"−{b['consumption_per_day']:.3f} мг/л/день" if b['consumption_per_day'] > 0 else "0",
                          help="Чисте від'ємне відхилення від очікуваного балансу")
                c4.metric("Накопичення / джерело",
                          f"+{b['organic_per_day']:.3f} мг/л/день" if b['organic_per_day'] > 0 else "0",
                          help="Органіка, нітрифікація, блокування — невидиме зростання")

                # Пояснення
                if b['organic_per_day'] > 0.1 and param == 'no3':
                    st.warning(f"⚠️ NO3 зростає на +{b['organic_per_day']:.2f} мг/л/день попри підміни. "
                               f"Можливі причини: розкладання органіки, перегодовування риб, "
                               f"недостатня підміна, стара субстрат.")
                if b['consumption_per_day'] > 0 and param == 'no3':
                    st.success(f"✅ Рослини споживають {b['consumption_per_day']:.2f} мг/л NO3/день")
                if b['invisible'] == 0:
                    st.info("Баланс збігається — підміна і добрива повністю пояснюють зміну.")

                # Мінібаланс у вигляді рівняння
                sign = "+" if b['net_change'] >= 0 else ""
                st.caption(
                    f"Баланс: {b['v_start']} "
                    f"− {b['wc_effect']:.2f} (підміна) "
                    f"+ {b['fert_added']:.2f} (добриво) "
                    f"+ {b['invisible']:+.2f} (невидима зміна) "
                    f"= {b['v_end']} мг/л"
                )
else:
    if len(tests) == 1:
        st.info("Введіть ще один тест щоб побачити аналіз балансу між ними.")
    else:
        st.info("Введіть мінімум два тести в журналі щоб побачити аналіз.")

# ================================================================
# БЛОК D — СПОЖИВАННЯ (з балансу або ручний ввід)
# ================================================================
st.divider()
st.header("📊 D. Споживання елементів")

# Авторозрахунок з останньої пари тестів
auto_cons = {'no3': None, 'po4': None, 'k': None}
auto_org  = {'no3': 0.0,  'po4': 0.0,  'k': 0.0}

if len(tests) >= 2:
    bal_auto = compute_balance(tests[-2], tests[-1], tank_vol)
    for p in ['no3','po4','k']:
        auto_cons[p] = bal_auto[p]['consumption_per_day']
        auto_org[p]  = bal_auto[p]['organic_per_day']
    st.success("🤖 Споживання розраховано автоматично з двох останніх тестів. "
               "Можна скоригувати вручну нижче.")
else:
    st.info("💡 Після введення 2+ тестів споживання розраховується автоматично.")

dc1, dc2, dc3 = st.columns(3)
with dc1:
    d_no3 = st.number_input("Споживання NO3 (мг/л/день)",
                             value=float(auto_cons['no3'] or 2.0), step=0.1, format="%.2f", key="d_no3")
    o_no3 = st.number_input("Джерело NO3 (мг/л/день) — органіка",
                             value=float(auto_org['no3']), step=0.05, format="%.2f", key="o_no3",
                             help="Якщо NO3 зростає без внесення — введіть позитивне значення")
with dc2:
    d_po4 = st.number_input("Споживання PO4 (мг/л/день)",
                             value=float(auto_cons['po4'] or 0.1), step=0.01, format="%.3f", key="d_po4")
    o_po4 = st.number_input("Джерело PO4 (мг/л/день)",
                             value=float(auto_org['po4']), step=0.01, format="%.3f", key="o_po4")
with dc3:
    d_k = st.number_input("Споживання K (мг/л/день)",
                           value=float(auto_cons['k'] or 1.0), step=0.1, format="%.2f", key="d_k")
    o_k = st.number_input("Джерело K (мг/л/день)",
                           value=float(auto_org['k']), step=0.05, format="%.2f", key="o_k")

# ================================================================
# БЛОК E — РЕМІНЕРАЛІЗАТОР
# ================================================================
st.divider()
st.header("💎 E. Ремінералізатор")
with st.expander("Розрахунок солей для осмосу"):
    re1, re2 = st.columns(2)
    with re1:
        r_vol     = st.number_input("Літрів осмосу", value=10.0, step=5.0, key="r_vol")
        r_gh      = st.slider("Цільовий GH (°dH)", 1.0, 20.0, 6.0, 0.5, key="r_gh")
        r_kh      = st.slider("Цільовий KH (°dH)", 0.0, 15.0, 2.0, 0.5, key="r_kh")
        r_camg    = st.slider("Цільове Ca:Mg",      1.0, 6.0,  3.0, 0.5, key="r_camg")
    with re2:
        denom  = (r_camg / 5.1) + (1.0 / 4.3)
        mg_mgl = r_gh / denom if denom > 0 else 0
        ca_mgl = r_camg * mg_mgl
        total_ca_g     = ca_mgl * r_vol / 1000
        total_mg_g     = mg_mgl * r_vol / 1000
        caco3_g        = r_kh * 17.86 * r_vol / 1000
        ca_from_caco3  = caco3_g * 0.4
        remaining_ca_g = max(0, total_ca_g - ca_from_caco3)
        cacl2_g        = remaining_ca_g / 0.273 if remaining_ca_g > 0 else 0
        mgso4_g        = total_mg_g / 0.0986 if total_mg_g > 0 else 0
        st.success(f"""
        **Для {r_vol:.0f} л осмосу:**
        🧂 CaCO₃: **{caco3_g:.3f} г**
        🧂 CaCl₂·2H₂O: **{cacl2_g:.3f} г**
        🧂 MgSO₄·7H₂O: **{mgso4_g:.3f} г**
        Ca = {ca_mgl:.1f} мг/л | Mg = {mg_mgl:.1f} мг/л | TDS ~{r_gh*10+r_kh*5:.0f} ppm
        """)

# ================================================================
# БЛОК F — ДОЗУВАННЯ І ПРОГНОЗ
# ================================================================
st.divider()
st.header("🧪 F. Дозування добрив і прогноз")

st.caption("Вкажіть щоденне дозування — прогноз будується на основі реального споживання з блоку D.")

fc1, fc2, fc3 = st.columns(3)
with fc1:
    dose_n_ml   = st.number_input("N: мл/день", value=0.0, step=1.0, key="dose_n")
    dose_n_conc = st.number_input("N: г/л", value=50.0, step=5.0, key="dose_n_conc")
    dose_n_mgl  = dose_n_ml * dose_n_conc / tank_vol if tank_vol > 0 else 0
    st.caption(f"→ +{dose_n_mgl:.2f} мг/л NO3/день")
with fc2:
    dose_p_ml   = st.number_input("P: мл/день", value=0.0, step=0.5, key="dose_p")
    dose_p_conc = st.number_input("P: г/л", value=5.0, step=0.5, key="dose_p_conc")
    dose_p_mgl  = dose_p_ml * dose_p_conc / tank_vol if tank_vol > 0 else 0
    st.caption(f"→ +{dose_p_mgl:.3f} мг/л PO4/день")
with fc3:
    dose_k_ml   = st.number_input("K: мл/день", value=0.0, step=1.0, key="dose_k")
    dose_k_conc = st.number_input("K: г/л", value=20.0, step=2.0, key="dose_k_conc")
    dose_k_mgl  = dose_k_ml * dose_k_conc / tank_vol if tank_vol > 0 else 0
    st.caption(f"→ +{dose_k_mgl:.2f} мг/л K/день")

st.divider()
wc_weekly_pct = st.slider("Підміна на тиждень (%)", 0, 80, 25, 5, key="wc_weekly")
wc_daily_frac = (wc_weekly_pct / 100) / 7

if last_test:
    start_vals  = {'no3': last_test['no3'], 'po4': last_test['po4'], 'k': last_test['k']}
    daily_fert  = {'no3': dose_n_mgl, 'po4': dose_p_mgl, 'k': dose_k_mgl}
    consumption = {'no3': d_no3, 'po4': d_po4, 'k': d_k}
    organic     = {'no3': o_no3, 'po4': o_po4, 'k': o_k}

    forecast = run_forecast(start_vals, consumption, organic, daily_fert, wc_daily_frac, forecast_days)
    df_fc = pd.DataFrame(forecast).set_index("День")

    # Симулятор «що якщо»
    with st.expander("🔬 Симулятор «Що якщо» — порівняти сценарії"):
        sc1, sc2, sc3, sc4 = st.columns(4)
        sim_n  = sc1.slider("N мл/день", 0.0, 30.0, float(dose_n_ml), 0.5, key="sim_n2")
        sim_p  = sc2.slider("P мл/день", 0.0, 20.0, float(dose_p_ml), 0.1, key="sim_p2")
        sim_k  = sc3.slider("K мл/день", 0.0, 30.0, float(dose_k_ml), 0.5, key="sim_k2")
        sim_wc = sc4.slider("Підміна %/тижд.", 0, 80, wc_weekly_pct, 5, key="sim_wc2")

        sim_fert = {
            'no3': sim_n * dose_n_conc / tank_vol if tank_vol > 0 else 0,
            'po4': sim_p * dose_p_conc / tank_vol if tank_vol > 0 else 0,
            'k':   sim_k * dose_k_conc / tank_vol if tank_vol > 0 else 0,
        }
        sim_fc = run_forecast(start_vals, consumption, organic, sim_fert,
                              (sim_wc/100)/7, forecast_days)
        df_sim = pd.DataFrame(sim_fc).set_index("День")

        df_cmp = df_fc[["NO3"]].rename(columns={"NO3": "NO3 (поточне)"})
        df_cmp["NO3 (сценарій)"] = df_sim["NO3"]
        st.line_chart(df_cmp)

        end_base = forecast[-1]
        end_sim  = sim_fc[-1]
        m1, m2, m3 = st.columns(3)
        m1.metric(f"NO3 (сценарій, день {forecast_days})", f"{end_sim['NO3']:.1f}",
                  delta=f"{end_sim['NO3']-end_base['NO3']:+.1f} vs поточне")
        m2.metric(f"PO4 (сценарій, день {forecast_days})", f"{end_sim['PO4']:.2f}",
                  delta=f"{end_sim['PO4']-end_base['PO4']:+.2f} vs поточне")
        m3.metric(f"K (сценарій, день {forecast_days})", f"{end_sim['K']:.1f}",
                  delta=f"{end_sim['K']-end_base['K']:+.1f} vs поточне")

    st.subheader(f"📈 Прогноз на {forecast_days} днів")
    st.line_chart(df_fc)

    # Попередження по прогнозу
    k_range = get_k_range(gh)
    f_end   = forecast[-1]
    if f_end['NO3'] < 3:
        st.error(f"⚠️ День {forecast_days}: NO3 впаде до {f_end['NO3']} мг/л — критично!")
    if f_end['PO4'] < 0.1:
        st.error(f"⚠️ День {forecast_days}: PO4 впаде до {f_end['PO4']} мг/л — критично!")
    if f_end['K'] < k_range['min']:
        st.error(f"⚠️ День {forecast_days}: K впаде до {f_end['K']} мг/л — нижче мінімуму!")
    if f_end['NO3'] > 40:
        st.warning(f"⚠️ День {forecast_days}: NO3 перевищить 40 мг/л — зменште дозу або збільшіть підміну.")

    # Waterfall за тиждень
    with st.expander("🌊 Waterfall — баланс за тиждень"):
        wf_sel = st.selectbox("Елемент:", ["NO3", "PO4", "K"], key="wf_sel")
        param_map = {"NO3": ("no3", d_no3, dose_n_mgl, o_no3, start_vals['no3']),
                     "PO4": ("po4", d_po4, dose_p_mgl, o_po4, start_vals['po4']),
                     "K":   ("k",   d_k,   dose_k_mgl, o_k,   start_vals['k'])}
        _, cons_v, fert_v, org_v, start_v = param_map[wf_sel]

        n_days_wf = 7
        wc_v   = start_v * wc_daily_frac * n_days_wf
        total_cons = cons_v * n_days_wf
        total_fert = fert_v * n_days_wf
        total_org  = org_v  * n_days_wf
        end_v  = start_v - wc_v - total_cons + total_fert + total_org

        wf_df = pd.DataFrame({
            "Компонент": ["Початок", "− Підміна", "− Споживання", "+ Добриво", "+ Органіка/джерело", "Кінець"],
            "мг/л":      [start_v,  -wc_v, -total_cons, total_fert, total_org, end_v]
        }).set_index("Компонент")
        wfw1, wfw2 = st.columns([2, 1])
        with wfw1:
            st.bar_chart(wf_df)
        with wfw2:
            for row in wf_df.itertuples():
                st.metric(row.Index, f"{row._1:+.2f} мг/л" if row.Index not in ["Початок","Кінець"]
                          else f"{row._1:.2f} мг/л")
else:
    st.info("👆 Введіть перший тест в блоці А щоб побачити прогноз.")

# ================================================================
# БЛОК G — K/GH АНАЛІЗ
# ================================================================
st.divider()
st.header("🧂 G. K/GH аналіз")

k_range = get_k_range(gh)

if last_test:
    k_curr   = last_test['k']
    k_ratio  = k_curr / gh if gh > 0 else 0

    gk1, gk2, gk3 = st.columns(3)
    gk1.metric("Поточний K (з останнього тесту)", f"{k_curr:.1f} мг/л")
    gk2.metric("K/GH ratio", f"{k_ratio:.2f}", delta="норма 1.5–2.5")

    with gk3:
        if k_curr < k_range['min']:
            st.error(f"🔴 Критичний дефіцит K\nПідніміть до мінімуму {k_range['min']:.1f} мг/л")
        elif k_curr < k_range['opt_low']:
            st.warning(f"🟡 Дефіцит K — підніміть до {k_range['opt_low']:.0f} мг/л")
        elif k_curr <= k_range['opt_high']:
            st.success("✅ K в оптимальному діапазоні")
        elif k_curr <= k_range['max']:
            st.warning(f"🟡 Надлишок K — знизьте на {k_curr - k_range['opt_high']:.1f} мг/л")
        else:
            st.error("🔴 Критичний надлишок K")

    st.caption(f"Для GH={gh}°dH: мін {k_range['min']:.1f} | оптимум {k_range['opt_low']:.0f}–{k_range['opt_high']:.0f} | макс {k_range['max']:.1f} мг/л")

    # Прогноз K окремо (з реальним споживанням з блоку D)
    if last_test:
        k_forecast = []
        kv = k_curr
        for d in range(forecast_days + 1):
            k_forecast.append({'День': d, 'K (прогноз)': round(kv, 2),
                                'K opt_low': k_range['opt_low'],
                                'K opt_high': k_range['opt_high']})
            kv = clamp(kv * (1 - wc_daily_frac) + dose_k_mgl - d_k + o_k, 0, 500)
        st.line_chart(pd.DataFrame(k_forecast).set_index("День"))
        if k_forecast[-1]['K (прогноз)'] < k_range['opt_low']:
            st.warning(f"📉 Через {forecast_days} днів K опуститься до {k_forecast[-1]['K (прогноз)']:.1f} мг/л — нижче оптимуму. Збільшіть дозу K.")
else:
    st.info("Введіть тест щоб побачити аналіз K.")

# ================================================================
# БЛОК H — ШІ РЕКОМЕНДАЦІЇ
# ================================================================
st.divider()
st.header("🤖 H. Діагностика та рекомендації")

if last_test:
    no3_c = last_test['no3']
    po4_c = last_test['po4']
    k_c   = last_test['k']
    co2_c = last_test['co2']

    col_h1, col_h2 = st.columns(2)

    with col_h1:
        st.subheader("📊 Поточний стан")

        # CO₂
        if co2_c < co2_lo:
            st.warning(f"🌬️ CO₂: {co2_c:.1f} мг/л — дефіцит (норма {co2_lo}–{co2_hi})")
        elif co2_c > co2_hi:
            st.error(f"🌬️ CO₂: {co2_c:.1f} мг/л — надлишок! Ризик для риб")
        else:
            st.success(f"✅ CO₂: {co2_c:.1f} мг/л — норма")

        # pH різниця ранок/вечір
        ph_diff = last_test['ph_morning'] - last_test['ph_evening']
        if ph_diff < 0.3:
            st.warning(f"⚠️ Різниця pH ранок/вечір = {ph_diff:.1f} — CO₂ працює слабо або вимкнений")
        elif ph_diff > 1.0:
            st.warning(f"⚠️ Різниця pH = {ph_diff:.1f} — дуже різка зміна CO₂")

        # N:P баланс
        if po4_c > 0:
            np_r = no3_c / po4_c
            if np_r < redfield * 0.8:
                st.warning(f"⚠️ N:P = {np_r:.1f}:1 — дефіцит N (ціль {redfield}:1)")
            elif np_r > redfield * 1.2:
                st.warning(f"⚠️ N:P = {np_r:.1f}:1 — дефіцит P (ціль {redfield}:1)")
            else:
                st.success(f"✅ N:P = {np_r:.1f}:1 — баланс")

        # K/GH
        if gh > 0:
            if k_c < k_range['opt_low']:
                st.warning(f"⚠️ K/GH = {k_c/gh:.2f} — дефіцит K")
            elif k_c > k_range['opt_high']:
                st.warning(f"⚠️ K/GH = {k_c/gh:.2f} — надлишок K")
            else:
                st.success(f"✅ K/GH = {k_c/gh:.2f} — норма")

        st.info(f"🌊 Ризик водоростей: {algae_risk(no3_c, po4_c)}")
        st.info(f"💡 Світло: {light_rec(co2_c, no3_c, po4_c)}")

    with col_h2:
        st.subheader("💡 Рекомендації")
        recs = []
        if no3_c < 5:
            recs.append(("error",   "NO3 критично низький (<5) — збільшіть N"))
        elif no3_c < 10:
            recs.append(("warning", "NO3 низький — додайте N на 20%"))
        elif no3_c > 40:
            recs.append(("error",   "NO3 дуже високий (>40) — зменшіть N або підміну"))
        elif no3_c > 30:
            recs.append(("warning", "NO3 підвищений — зменшіть N на 10-20%"))

        if o_no3 > 0.5:
            recs.append(("warning",
                f"NO3 росте сам (+{o_no3:.2f}/день) — перевірте органіку, "
                f"перегодовування, ґрунт"))

        if po4_c < 0.2:
            recs.append(("error",   "PO4 критично низький — збільшіть P"))
        elif po4_c < 0.5:
            recs.append(("warning", "PO4 низький — P може бути лімітуючим"))
        elif po4_c > 2.5:
            recs.append(("error",   "PO4 дуже високий — ризик водоростей"))

        if k_c < k_range['opt_low']:
            recs.append(("error",   f"K дефіцит — додайте до {k_range['opt_low']:.0f} мг/л"))
        elif k_c > k_range['opt_high']:
            recs.append(("warning", "K надлишок — можливе блокування Ca/Mg"))

        if co2_c < co2_lo:
            recs.append(("error",   f"CO₂ дефіцит ({co2_c:.1f} < {co2_lo}) — збільшіть подачу"))
        elif co2_c > co2_hi:
            recs.append(("error",   f"CO₂ надлишок ({co2_c:.1f} > {co2_hi}) — ризик для риб!"))

        if recs:
            for level, msg in recs[:6]:
                if level == "error":
                    st.error(f"🔴 {msg}")
                else:
                    st.warning(f"🟡 {msg}")
        else:
            st.success("✅ Всі параметри в нормі!")

        # Корекція дозування
        if last_test and 'f_end' in dir():
            st.subheader("📅 Корекція дози")
            def dose_suggestion(current_val, target_val, cons_per_day, conc_g_l, current_ml, days_n, tv):
                gap = target_val - current_val
                if abs(gap) < 0.5:
                    return current_ml, "✅ без змін"
                extra_per_day = gap / max(days_n, 1)
                delta_ml = extra_per_day * tv / conc_g_l if conc_g_l > 0 else 0
                new_ml = max(0, current_ml + delta_ml)
                sign = "+" if delta_ml > 0 else ""
                return new_ml, f"{sign}{delta_ml:.2f} мл/день"

            new_n, act_n = dose_suggestion(no3_c, target_no3, d_no3, dose_n_conc, dose_n_ml, forecast_days, tank_vol)
            new_p, act_p = dose_suggestion(po4_c, target_po4, d_po4, dose_p_conc, dose_p_ml, forecast_days, tank_vol)
            new_k, act_k = dose_suggestion(k_c,   target_k,   d_k,   dose_k_conc, dose_k_ml, forecast_days, tank_vol)

            dm1, dm2, dm3 = st.columns(3)
            dm1.metric("N доза", f"{dose_n_ml:.1f}→{new_n:.1f} мл/день", delta=act_n)
            dm2.metric("P доза", f"{dose_p_ml:.2f}→{new_p:.2f} мл/день", delta=act_p)
            dm3.metric("K доза", f"{dose_k_ml:.1f}→{new_k:.1f} мл/день", delta=act_k)
            st.caption("💡 Змінюйте поступово, не більше 20% за раз")
else:
    st.info("Введіть тест щоб отримати рекомендації.")

# ================================================================
# БЛОК I — ТЕПЛОВА КАРТА
# ================================================================
if last_test and len(forecast) > 0:
    with st.expander("🌡️ I. Теплова карта прогнозу"):
        k_r = get_k_range(gh)
        limits = {
            'NO3': (5, 30),
            'PO4': (0.2, 1.5),
            'K':   (k_r['opt_low'], k_r['opt_high'])
        }
        hm = {}
        for col, (lo, hi) in limits.items():
            row = []
            for rec in forecast:
                v = rec[col]
                if   v < lo * 0.6: row.append(-2)
                elif v < lo:        row.append(-1)
                elif v <= hi:       row.append(0)
                elif v <= hi * 1.4: row.append(1)
                else:               row.append(2)
            hm[col] = row

        df_hm = pd.DataFrame(hm, index=[f"День {d}" for d in range(forecast_days+1)])
        st.caption("−2 критичний дефіцит | −1 дефіцит | 0 норма | +1 підвищений | +2 надлишок")
        st.dataframe(df_hm.style.background_gradient(cmap='RdYlGn', vmin=-2, vmax=2),
                     use_container_width=True)

# ================================================================
# БЛОК J — ЗВІТ
# ================================================================
st.divider()
with st.expander("📋 J. Звіт для журналу"):
    if last_test:
        report_lines = [
            "=== TOXICODE AQUARIUM V12 ===",
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"Об'єм: {tank_vol} л | GH: {gh}°dH | KH: {kh}°dH",
            f"CO₂: {last_test['co2']:.1f} мг/л | pH: {last_test['ph_morning']}→{last_test['ph_evening']}",
            "",
            "ПОТОЧНІ ПАРАМЕТРИ (останній тест)",
            f"NO3: {last_test['no3']:.1f}  PO4: {last_test['po4']:.2f}  K: {last_test['k']:.1f} мг/л",
            "",
            "СПОЖИВАННЯ / ДЖЕРЕЛО",
            f"NO3: −{d_no3:.2f} / +{o_no3:.2f} мг/л/день",
            f"PO4: −{d_po4:.3f} / +{o_po4:.3f} мг/л/день",
            f"K:   −{d_k:.2f} / +{o_k:.2f} мг/л/день",
            "",
            f"ПРОГНОЗ ЧЕРЕЗ {forecast_days} ДНІВ",
            f"NO3: {forecast[-1]['NO3']:.1f}  PO4: {forecast[-1]['PO4']:.2f}  K: {forecast[-1]['K']:.1f} мг/л",
            "",
            f"ШІ: {algae_risk(last_test['no3'], last_test['po4'])}",
            "================================",
        ]
        st.code("\n".join(report_lines), language="text")
    else:
        st.info("Введіть тест щоб згенерувати звіт.")

# ================================================================
# БЛОК K — ВАЛІДАЦІЯ
# ================================================================
with st.expander("🛡️ K. Валідація"):
    if last_test:
        k_r = get_k_range(gh)
        rows = [
            ("NO3",  last_test['no3'],  "5–40",       5 <= last_test['no3'] <= 40),
            ("PO4",  last_test['po4'],  "0.2–2.5",    0.2 <= last_test['po4'] <= 2.5),
            ("CO₂",  last_test['co2'],  f"{co2_lo}–{co2_hi}", co2_lo <= last_test['co2'] <= co2_hi),
            ("K/GH", round(last_test['k']/gh,2) if gh>0 else 0, "1.5–2.5",
             1.5 <= (last_test['k']/gh if gh>0 else 0) <= 2.5),
        ]
        md = "| Параметр | Значення | Норма | Статус |\n|---|---|---|---|\n"
        for name, val, norm, ok in rows:
            md += f"| {name} | {val} | {norm} | {'✅' if ok else '⚠️'} |\n"
        st.markdown(md)
    else:
        st.info("Введіть тест щоб побачити валідацію.")

st.caption("⚡ Toxicode V12 | Журнал подій | Реальний баланс | Діагностика джерел | Симулятор сценаріїв")
