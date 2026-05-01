
import streamlit as st
import math

st.set_page_config(page_title="Football Model", layout="centered")
st.title("Live Football Model")

# --- INPUTS ---
st.markdown("### Team averages (full match)")

home_shot = st.number_input("Home Shots", value=12.0)
away_shot = st.number_input("Away Shots", value=11.0)

home_sot = st.number_input("Home Shots on Target", value=4.5)
away_sot = st.number_input("Away Shots on Target", value=4.0)

home_throw = st.number_input("Home Throw-ins", value=18.0)
away_throw = st.number_input("Away Throw-ins", value=17.0)

home_foul = st.number_input("Home Fouls", value=12.0)
away_foul = st.number_input("Away Fouls", value=11.0)

home_corner = st.number_input("Home Corners", value=5.0)
away_corner = st.number_input("Away Corners", value=4.5)

home_card = st.number_input("Home Cards", value=1.5)
away_card = st.number_input("Away Cards", value=1.2)

home_gk = st.number_input("Home Goal Kicks", value=6.0)
away_gk = st.number_input("Away Goal Kicks", value=6.0)

home_off = st.number_input("Home Offsides", value=2.0)
away_off = st.number_input("Away Offsides", value=2.0)

st.markdown("---")

score_state = st.selectbox("Score State", ["Draw", "Home Losing", "Away Losing"])

# --- INTERVAL ---
start_min = st.slider("Start minute", 1, 90, 10)

if start_min < 45:
    max_end = min(start_min + 5, 45)
else:
    max_end = min(start_min + 5, 90)

end_min = st.slider("End minute", start_min + 1, max_end, start_min + 1)

minutes = end_min - start_min

# --- CONSTANTS ---
margin = 0.08
fh_min = 46.5
sh_min = 48.5

def prob(lmbda):
    return 1 - math.exp(-lmbda)

def odds(p):
    return (1 / p) * (1 - margin) if p > 0 else 0

def calc_lambda(avg, total_minutes, interval):
    return (avg / total_minutes) * interval

def split(avg):
    return avg * 0.48, avg * 0.52

# --- GAP ---
ratio = max(home_shot, away_shot) / max(1, min(home_shot, away_shot))
gap = "balanced" if ratio < 1.2 else "medium" if ratio < 2 else "strong"

# --- STATE FUNCTION ---
def apply(name, lh, la, base_total):

    # ❌ არ ვეხებით
    if name in ["Fouls", "Offsides", "Cards"]:
        return lh, la

    # GK mirror
    if name == "Goal Kicks":
        if score_state == "Home Losing":
            lh *= 0.90
            la *= 1.10
        elif score_state == "Away Losing":
            lh *= 1.10
            la *= 0.90
        return lh, la

    # multipliers
    if name == "Shots":
        sp, mp, wr = 1.30, 1.18, 0.93
    elif name == "Shots on Target":
        sp, mp, wr = 1.22, 1.15, 0.95
    elif name == "Corners":
        sp, mp, wr = 1.22, 1.15, 0.95
    elif name == "Throw-ins":
        sp, mp, wr = 1.20, 1.12, 0.96
    else:
        return lh, la

    # balanced symmetry
    if gap == "balanced":
        if score_state == "Home Losing":
            lh *= mp
            la *= wr
        elif score_state == "Away Losing":
            la *= mp
            lh *= wr
    else:
        if score_state == "Home Losing":
            if gap == "medium":
                lh *= mp
            else:
                lh *= sp
        elif score_state == "Away Losing":
            if gap == "medium":
                la *= mp
            else:
                la *= sp

    # 🔥 TOTAL FREEZE (Shots + SOT only, near balanced)
    if name in ["Shots", "Shots on Target"]:
        ratio_local = max(lh, la) / max(1e-6, min(lh, la))

        if ratio_local < 1.25:
            new_total = lh + la
            if new_total > 0:
                scale = base_total / new_total
                lh *= scale
                la *= scale

    return lh, la

# --- BOOSTS ---
throw_boost = 1 + (minutes / 10) * 0.15
shot_interval_boost = 1 + (minutes / 10) * 0.15

early_throw_boost = 1
if start_min <= 10:
    early_throw_boost = 1 + ((10 - start_min) / 10) * 0.12

# --- CARD DIST ---
card_dist = [
    (1, 15, 0.05), (15, 30, 0.11), (30, 45, 0.175),
    (45, 60, 0.15), (60, 75, 0.18), (75, 90, 0.34),
]

def card_lambda(avg, start, end):
    total = 0
    for s, e, w in card_dist:
        overlap = max(0, min(end, e) - max(start, s))
        if overlap > 0:
            total += avg * w * (overlap / (e - s))
    return total

# --- MARKETS ---
markets = {
    "Shots": (home_shot, away_shot, 1.17),
    "Shots on Target": (home_sot, away_sot, 1.14),
    "Fouls": (home_foul, away_foul, 1.11),
    "Corners": (home_corner, away_corner, 1.15),
    "Throw-ins": (home_throw, away_throw, None),
    "Cards": (home_card, away_card, None),
    "Goal Kicks": (home_gk, away_gk, 1.07),
    "Offsides": (home_off, away_off, None),
}

st.subheader("Results")

for name, (home, away, adj) in markets.items():

    if name == "Cards":
        l_home = card_lambda(home, start_min, end_min)
        l_away = card_lambda(away, start_min, end_min)

    elif name == "Offsides":
        if end_min <= 45:
            l_home = calc_lambda(home, fh_min, minutes)
            l_away = calc_lambda(away, fh_min, minutes)
        else:
            l_home = calc_lambda(home, sh_min, minutes)
            l_away = calc_lambda(away, sh_min, minutes)

    else:
        fh_home, sh_home = split(home)
        fh_away, sh_away = split(away)

        if name == "Throw-ins":
            sh_home = fh_home - 0.25
            sh_away = fh_away - 0.25
        else:
            sh_home = fh_home * adj
            sh_away = fh_away * adj

        if end_min <= 45:
            l_home = calc_lambda(fh_home, fh_min, minutes)
            l_away = calc_lambda(fh_away, fh_min, minutes)
        else:
            l_home = calc_lambda(sh_home, sh_min, minutes)
            l_away = calc_lambda(sh_away, sh_min, minutes)

    # BOOSTS unchanged
    if name == "Throw-ins":
        l_home *= throw_boost * early_throw_boost
        l_away *= throw_boost * early_throw_boost

    if name in ["Shots", "Shots on Target"]:
        l_home *= shot_interval_boost
        l_away *= shot_interval_boost

    base_total = l_home + l_away

    # 🔥 STATE
    l_home, l_away = apply(name, l_home, l_away, base_total)

    l_total = l_home + l_away

    p_home = prob(l_home)
    p_away = prob(l_away)
    p_total = prob(l_total)

    st.markdown(f"### {name}")
    st.write(f"Home → {round(p_home*100,1)}% | Odds: {round(odds(p_home),2)}")
    st.write(f"Away → {round(p_away*100,1)}% | Odds: {round(odds(p_away),2)}")
    st.write(f"Total → {round(p_total*100,1)}% | Odds: {round(odds(p_total),2)}")
    st.markdown("---")
