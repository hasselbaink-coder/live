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

# --- SCORE STATE ---
score_state = st.selectbox(
    "Score State",
    ["Draw", "Home Losing", "Away Losing", "Home Losing BIG", "Away Losing BIG"]
)

# --- INTERVAL ---
start_min = st.slider("Start minute", 1, 90, 10)

if start_min < 45:
    max_end = min(start_min + 5, 45)
else:
    max_end = min(start_min + 5, 90)

end_min = st.slider("End minute", start_min + 1, max_end, start_min + 1)

minutes = end_min - start_min
st.write(f"Interval: {minutes} minute(s)")

# --- CONSTANTS ---
margin = 0.08
fh_min = 46.5
sh_min = 48.5

# --- FUNCTIONS ---
def prob(lmbda):
    return 1 - math.exp(-lmbda)

def odds(p):
    return (1 / p) * (1 - margin) if p > 0 else 0

def calc_lambda(avg, total_minutes, interval):
    return (avg / total_minutes) * interval

def split(avg):
    return avg * 0.48, avg * 0.52


# =========================
# GAP LOGIC (shots based)
# =========================
if min(home_shot, away_shot) == 0:
    ratio = 1
else:
    ratio = max(home_shot, away_shot) / min(home_shot, away_shot)

if ratio < 1.2:
    gap_level = "balanced"
elif ratio < 2.0:
    gap_level = "medium"
else:
    gap_level = "strong"


# =========================
# GAME STATE ENGINE
# =========================
def apply_game_state(name, l_home, l_away, state, start_min,
                     gap_level, home_shot, away_shot):

    is_home_strong = home_shot > away_shot
    is_away_strong = away_shot > home_shot

    # MARKET WEIGHTS
    if name == "Shots":
        strong_push = 1.30
        medium_push = 1.18
        win_reduce = 0.93

    elif name == "Shots on Target":
        strong_push = 1.22
        medium_push = 1.15
        win_reduce = 0.95

    elif name == "Corners":
        strong_push = 1.22
        medium_push = 1.15
        win_reduce = 0.95

    elif name == "Throw-ins":
        strong_push = 1.20
        medium_push = 1.12
        win_reduce = 0.96

    else:
        return l_home, l_away

    # minute boost
    factor = max(0, (start_min - 60) / 30)
    strong_push += factor * 0.10
    medium_push += factor * 0.07

    # =====================
    # HOME LOSING
    # =====================
    if state == "Home Losing":

        if gap_level == "balanced":
            l_home *= medium_push
            l_away *= win_reduce

        elif gap_level == "medium":
            if is_home_strong:
                l_home *= medium_push
            else:
                l_away *= 1.07

        elif gap_level == "strong":
            if is_home_strong:
                l_home *= strong_push
            else:
                l_home *= 1.05

    # =====================
    # AWAY LOSING
    # =====================
    elif state == "Away Losing":

        if gap_level == "balanced":
            l_away *= medium_push
            l_home *= win_reduce

        elif gap_level == "medium":
            if is_away_strong:
                l_away *= medium_push
            else:
                l_home *= 1.07

        elif gap_level == "strong":
            if is_away_strong:
                l_away *= strong_push
            else:
                l_away *= 1.05

    # =====================
    # BIG STATES (FIXED)
    # =====================
    elif state == "Home Losing BIG":
        if is_home_strong:
            l_home *= strong_push * 1.15
        else:
            l_home *= 1.05

    elif state == "Away Losing BIG":
        if is_away_strong:
            l_away *= strong_push * 1.15
        else:
            l_away *= 1.05

    return l_home, l_away


# --- CARD DISTRIBUTION ---
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

total_lambdas = {}

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

    # base boosts
    throw_boost = 1 + (minutes / 10) * 0.15
    shot_interval_boost = 1 + (minutes / 10) * 0.15

    if name == "Throw-ins":
        early = 1
        if start_min <= 10:
            early = 1 + ((10 - start_min) / 10) * 0.12
        l_home *= throw_boost * early
        l_away *= throw_boost * early

    if name in ["Shots", "Shots on Target"]:
        l_home *= shot_interval_boost
        l_away *= shot_interval_boost

    # late game
    if start_min >= 75 and name not in ["Cards", "Offsides", "Fouls"]:
        factor = (start_min - 75) / 15

        if name == "Shots":
            l_home *= 1 + factor * 0.30
            l_away *= 1 + factor * 0.30

        elif name == "Shots on Target":
            l_home *= 1 + factor * 0.22
            l_away *= 1 + factor * 0.22

        elif name == "Corners":
            l_home *= 1 + factor * 0.25
            l_away *= 1 + factor * 0.25

        elif name == "Goal Kicks":
            l_home *= 1 + factor * 0.10
            l_away *= 1 + factor * 0.10

    # save total
    l_total_before = l_home + l_away

    # apply game state
    l_home, l_away = apply_game_state(
        name, l_home, l_away,
        score_state, start_min,
        gap_level, home_shot, away_shot
    )

    # normalization
    normalize = False

    if name in ["Shots on Target", "Corners", "Throw-ins"]:
        normalize = True

    elif name == "Shots" and gap_level != "strong":
        normalize = True

    if normalize:
        new_total = l_home + l_away
        if new_total > 0:
            scale = l_total_before / new_total
            l_home *= scale
            l_away *= scale

    l_total = l_home + l_away
    total_lambdas[name] = l_total

    p_home = prob(l_home)
    p_away = prob(l_away)
    p_total = prob(l_total)

    st.markdown(f"### {name}")
    st.write(f"Home → {round(p_home*100,1)}% | Odds: {round(odds(p_home),2)}")
    st.write(f"Away → {round(p_away*100,1)}% | Odds: {round(odds(p_away),2)}")
    st.write(f"Total → {round(p_total*100,1)}% | Odds: {round(odds(p_total),2)}")
    st.markdown("---")
