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

# 🔥 GAP IMPACT
def get_impact(home_avg, away_avg):
    stronger = max(home_avg, away_avg)
    weaker = min(home_avg, away_avg)
    if stronger == 0:
        return 1
    ratio = weaker / stronger
    return ratio ** 0.5

# 🔥 GAME STATE FUNCTION
def apply_game_state(name, l_home, l_away, state, start_min, home_avg, away_avg):

    impact = get_impact(home_avg, away_avg)

    # upset boost (თუ სუსტი იგებს)
    if (state == "Home Losing" and home_avg < away_avg) or \
       (state == "Away Losing" and away_avg < home_avg):
        impact *= 1.25

    factor = max(0, (start_min - 60) / 30)
    extra = factor * 0.10

    base_small = {
        "Shots": 1.15,
        "Shots on Target": 1.12,
        "Corners": 1.10,
        "Throw-ins": 1.05
    }

    base_big = {
        "Shots": 1.25,
        "Shots on Target": 1.20,
        "Corners": 1.15,
        "Throw-ins": 1.08
    }

    reduce_small = 0.95
    reduce_big = 0.92

    if state == "Home Losing":
        if name in base_small:
            mult = 1 + (base_small[name] - 1) * impact + extra
            l_home *= mult
            if name in ["Shots", "Corners"]:
                l_away *= reduce_small

    elif state == "Away Losing":
        if name in base_small:
            mult = 1 + (base_small[name] - 1) * impact + extra
            l_away *= mult
            if name in ["Shots", "Corners"]:
                l_home *= reduce_small

    elif state == "Home Losing BIG":
        if name in base_big:
            mult = 1 + (base_big[name] - 1) * impact + extra
            l_home *= mult
            if name in ["Shots", "Corners"]:
                l_away *= reduce_big

    elif state == "Away Losing BIG":
        if name in base_big:
            mult = 1 + (base_big[name] - 1) * impact + extra
            l_away *= mult
            if name in ["Shots", "Corners"]:
                l_home *= reduce_big

    return l_home, l_away

# --- MARKETS ---
markets = {
    "Shots": (home_shot, away_shot, 1.17),
    "Shots on Target": (home_sot, away_sot, 1.14),
    "Corners": (home_corner, away_corner, 1.15),
    "Throw-ins": (home_throw, away_throw, None),
}

st.subheader("Live Adjusted Markets")

for name, (home, away, adj) in markets.items():

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

    # 🔥 APPLY GAME STATE
    l_home, l_away = apply_game_state(name, l_home, l_away, score_state, start_min, home, away)

    p_home = prob(l_home)
    p_away = prob(l_away)

    st.markdown(f"### {name}")
    st.write(f"Home Odds: {round(odds(p_home),2)}")
    st.write(f"Away Odds: {round(odds(p_away),2)}")
    st.markdown("---")
