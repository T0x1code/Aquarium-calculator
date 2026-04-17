import streamlit as st
import pandas as pd

st.set_page_config(page_title="Toxicode Aquarium System V7.4", layout="wide")
st.title("🌿 Toxicode Aquarium System V7.4 Pro")

# ---------------- 1. SIDEBAR: ГЛОБАЛЬНІ ЦІЛІ ----------------
with st.sidebar:
    st.header("📏 Конфігурація")
    tank_vol = st.number_input("Чистий об'єм води (л)", value=200.0)
    
    st.divider()
    st.subheader("🎯 Ваші ідеальні цілі")
    target_no3 = st.number_input("Ціль NO3 (мг/л)", value=15.0)
    target_po4 = st.number_input("Ціль PO4 (мг/л)", value=1.0)
    target_k = st.number_input("Ціль K (мг/л)", value=15.0)
    target_tds = st.number_input("Ціль TDS", value=120.0)
    
    st.divider()
    days = st.slider("Період прогнозу (днів)", 1, 14, 7)

# ---------------- 2. РОЗРАХУНОК РЕАЛЬНОГО СПОЖИВАННЯ ----------------
st.header("📉 1. Калькулятор реального споживання")
st.caption("Введіть результати тестів з різницею в часі, щоб дізнатися, скільки реально "їсть" ваш акваріум.")
with st.expander("Відкрити калькулятор (NO3, PO4, K)"):
    tab1, tab2, tab3 = st.tabs(["Азот (NO3)", "Фосфор (PO4)", "Калій (K)"])
    
    def calc_cons(tab, name):
        with tab:
            c1, c2, c3 = st.columns(3)
            prev = c1.number_input(f"Минулий тест {name}", value=15.0, key=f"p_{name}")
            curr = c2.number_input(f"Сьогоднішній тест {name}", value=10.0, key=f"c_{name}")
            added = c3.number_input(f"Внесено добрив за період ({name})", value=0.0, key=f"a_{name}")
            d_pass = st.number_input("Днів між тестами", value=7, min_value=1, key=f"d_{name}")
            cons = (prev + added - curr) / d_pass
            st.info(f"**Ваше реальне споживання {name}:** {max(cons, 0):.2f} мг/л в день")

    calc_cons(tab1, "NO3")
    calc_cons(tab2, "PO4")
    calc_cons(tab3, "K")

st.divider()

# ---------------- 3. ПОТОЧНІ ПАРАМЕТРИ ----------------
st.header("📋 2. Поточні параметри води")
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Тести (сьогодні)")
    no3 = st.number_input("Поточний NO3 мг/л", value=10.0)
    po4 = st.number_input("Поточний PO4 мг/л", value=0.5)
    k = st.number_input("Поточний K мг/л", value=10.0)
    base_tds = st.number_input("Поточний TDS", value=150.0)

with c2:
    st.subheader("Жорсткість / pH")
    gh = st.number_input("GH", value=6)
    kh = st.number_input("KH", value=4)
    ph = st.number_input("pH", value=6.8)

with c3:
    st.subheader("Споживання (з калькулятора вище)")
    daily_no3 = st.number_input("Споживання NO3/день", value=2.0, step=0.1)
    daily_po4 = st.number_input("Споживання PO4/день", value=0.1, step=0.01)
    daily_k = st.number_input("Споживання K/день", value=1.0, step=0.1)

st.divider()

# ---------------- 4. ПІДМІНА ТА ДОБРИВА ----------------
col_act1, col_act2 = st.columns([1, 2])

with col_act1:
    st.header("💧 Підміна")
    change_l = st.number_input("Літри підміни (л)", value=50.0)
    water_tds = st.number_input("TDS свіжої води", value=110.0)
    
    pct = change_l / tank_vol if tank_vol > 0 else 0
    after_no3 = no3 * (1 - pct) 
    after_po4 = po4 * (1 - pct)
    after_k = k * (1 - pct)
    after_tds = base_tds * (1 - pct) + (water_tds * pct)

with col_act2:
    st.header("🧪 Дозування добрив (зараз)")
    cd1, cd2, cd3 = st.columns(3)
    conc_n = cd1.number_input("Конц. NO3 г/л", value=50.0)
    dose_n = cd1.number_input("Внести N мл", value=0.0)
    
    conc_p = cd2.number_input("Конц. PO4 г/л", value=5.0)
    dose_p = cd2.number_input("Внести P мл", value=0.0)
    
    conc_k = cd3.number_input("Конц. K г/л", value=20.0)
    dose_k = cd3.number_input("Внести K мл", value=0.0)

start_no3 = after_no3 + (dose_n * conc_n / tank_vol)
start_po4 = after_po4 + (dose_p * conc_p / tank_vol)
start_k = after_k + (dose_k * conc_k / tank_vol)

# ---------------- 5. ПРОГНОЗ ----------------
st.header("📈 3. Динаміка на тиждень")
forecast_data = []
for d in range(days + 1):
    forecast_data.append({
        "День": d,
        "NO3": max(start_no3 - daily_no3 * d, 0),
        "PO4": max(start_po4 - daily_po4 * d, 0),
        "K": max(start_k - daily_k * d, 0)
    })
df_forecast = pd.DataFrame(forecast_data).set_index("День")
st.line_chart(df_forecast)

# ---------------- 6. АНАЛІЗ ----------------
st.header("📊 4. Глибокий аналіз системи")
res1, res2, res3, res4 = st.columns(4)

co2 = 3 * kh * (10**(7 - ph))
ratio = start_no3 / start_po4 if start_po4 > 0 else 0
k_target_min = gh * 1.5

res1.metric(
    "CO2 (мг/л)", 
    f"{co2:.1f}", 
    help="Розрахунок за таблицею pH/KH. ВАЖЛИВО: Якщо у вас активний ґрунт (сойл), він збиває pH, тому ця формула покаже завищений (хибний) результат!"
)
res2.metric(
    "Редфілд (Пропорція N:P)", 
    f"{ratio:.1f} : 1", 
    help="Це співвідношення азоту до фосфору, а не їх концентрація у воді. Ідеальна пропорція 15:1 - 20:1."
)
res3.metric(
    "K:GH (Транспорт іонів)", 
    f"K = {start_k:.1f}", 
    f"Потрібно мінімум: {k_target_min:.1f}", 
    help="Щоб рослини могли засвоювати азот, Калію має бути як мінімум в 1.5 рази більше, ніж градусів GH."
)
res4.metric(
    "TDS (База після підміни)", 
    f"{after_tds:.0f}", 
    help="Це орієнтовний TDS після змішування старої і нової води. Він не враховує накопичення солей від щоденних добрив."
)

st.divider()

# ---------------- 7. КОРИГУВАННЯ ТА ПІДСУМОК ----------------
st.header("📝 5. План дій та Загальний стан")

f_no3 = df_forecast.iloc[-1]["NO3"]
f_po4 = df_forecast.iloc[-1]["PO4"]
f_k = df_forecast.iloc[-1]["K"]

def get_ml(current, target, conc, vol):
    if current < target:
        return ((target - current) * vol) / conc
    return 0

ml_n = get_ml(f_no3, target_no3, conc_n, tank_vol)
ml_p = get_ml(f_po4, target_po4, conc_p, tank_vol)
ml_k = get_ml(f_k, target_k, conc_k, tank_vol)

col_plan, col_summary = st.columns([1.5, 1])

with col_plan:
    st.subheader(f"Коригувальні дози (Дефіцит за {days} дн.)")
    st.caption("Щоб на кінець періоду не вийти в нуль, а залишитися на рівні ваших цілей, внесіть цю кількість розчину.")
    
    if ml_n > 0: st.warning(f"**N (Азот):** Дефіцит. Разово: **{ml_n:.1f} мл** АБО по **{ml_n/days:.1f} мл/день**.")
    else: st.success("**N (Азот):** Запасів достатньо.")
        
    if ml_p > 0: st.warning(f"**P (Фосфор):** Дефіцит. Разово: **{ml_p:.1f} мл** АБО по **{ml_p/days:.1f} мл/день**.")
    else: st.success("**P (Фосфор):** Запасів достатньо.")
        
    if ml_k > 0: st.warning(f"**K (Калій):** Дефіцит. Разово: **{ml_k:.1f} мл** АБО по **{ml_k/days:.1f} мл/день**.")
    else: st.success("**K (Калій):** Запасів достатньо.")

with col_summary:
    st.subheader("💡 Загальний висновок")
    issues = []
    
    if ratio < 10: issues.append("⚠️ Забагато фосфату відносно азоту (ризик синьо-зелених водоростей).")
    elif ratio > 25: issues.append("⚠️ Забагато азоту відносно фосфату (ризик ксенококусу).")
    
    if start_k < k_target_min: issues.append("🚫 Нестача калію! Рослини заблокують споживання нітратів (почнуться дірки на листі).")
    
    if (f_no3 == 0) or (f_po4 == 0): issues.append("📉 Прогноз показує обнулення макроелементів до кінця тижня (рослини зупинять ріст).")

    if not issues:
        st.success("🌟 Система у чудовому балансі! Параметри відповідають цілям, дефіцитів не передбачається. Продовжуйте в тому ж дусі.")
    else:
        for issue in issues:
            st.error(issue)
