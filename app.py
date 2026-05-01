
import streamlit as st
import math

st.set_page_config(page_title="Football Model", layout="centered")

st.title("Live Football Model")

# ---------------- INPUTS ----------------
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

# ---------------- STATE ----------------
score_state = st.selectbox(
    "Score State",
    ["Draw", "Home Losing", "Away Losing"]
)

start_min = st.slider("Start minute", 1, 90, 30)

if start_min < 45:
    max_end = min(start_min + 5, 45)
else:
    max_end = min(start_min + 5, 90)

end_min = st.slider("End minute", start_min + 1, max_end, start_min + 5)

minutes = end_min - start_min

# ---------------- CONSTANTS ----------------
margin = 0.08
fh_min = 46.5
sh_min = 48.5

def prob(l):
    return 1 - math.exp(-l)

def odds(p):
    return (1/p)*(1-margin) if p > 0 else 0

def calc(avg, total, m):
    return (avg/total)*m

def split(x):
    return x*0.48, x*0.52

# ---------------- GAP ----------------
ratio = max(home_shot, away_shot) / max(1, min(home_shot, away_shot))

if ratio < 1.2:
    gap = "balanced"
elif ratio < 2:
    gap = "medium"
else:
    gap = "strong"

# ---------------- GAME STATE ----------------
def apply(name, lh, la):

    home_strong = home_shot > away_shot
    away_strong = away_shot > home_shot

    if name == "Shots":
        sp, mp, wr = 1.30, 1.18, 0.93
    elif name == "Shots on Target":
        sp, mp, wr = 1.22, 1.15, 0.95
    elif name == "Corners":
        sp, mp, wr = 1.22, 1.15, 0.95
    elif name == "Throw-ins":
        sp, mp, wr = 1.20, 1.12, 0.96
    elif name == "Goal Kicks":
        sp, mp, wr = 1.10, 1.06, 0.97
    else:
        return lh, la

    # -------- BALANCED --------
    if gap == "balanced":
        if score_state == "Home Losing":
            lh *= mp
            la *= wr
        elif score_state == "Away Losing":
            la *= mp
            lh *= wr
        return lh, la

    # -------- GOAL KICK (FIXED CORRECTLY) --------
    if name == "Goal Kicks":

        if score_state == "Home Losing":
            la *= 1.25   # 🔥 opponent GK

        elif score_state == "Away Losing":
            lh *= 1.25

        return lh, la

    # -------- HOME LOSING --------
    if score_state == "Home Losing":

        if gap == "medium":
            if ratio < 1.5:
                lh *= mp
                la *= wr
            else:
                if home_strong:
                    lh *= mp

        elif gap == "strong":
            if home_strong:
                lh *= sp * 1.25
            else:
                lh *= 1.05

    # -------- AWAY LOSING --------
    elif score_state == "Away Losing":

        if gap == "medium":
            if ratio < 1.5:
                la *= mp
                lh *= wr
            else:
                if away_strong:
                    la *= mp

        elif gap == "strong":
            if away_strong:
                la *= sp * 1.25
            else:
                la *= 1.06

    return lh, la

# ---------------- CARD DIST ----------------
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

# ---------------- MARKETS ----------------
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

for name, (h, a, adj) in markets.items():

    if name == "Cards":
        lh = card_lambda(h, start_min, end_min)
        la = card_lambda(a, start_min, end_min)

    elif name == "Offsides":
        base = fh_min if end_min <= 45 else sh_min
        lh = calc(h, base, minutes)
        la = calc(a, base, minutes)

    else:
        fh_h, sh_h = split(h)
        fh_a, sh_a = split(a)

        if name == "Throw-ins":
            sh_h = fh_h - 0.25
            sh_a = fh_a - 0.25
        else:
            sh_h = fh_h * adj
            sh_a = fh_a * adj

        if end_min <= 45:
            lh = calc(fh_h, fh_min, minutes)
            la = calc(fh_a, fh_min, minutes)
        else:
            lh = calc(sh_h, sh_min, minutes)
            la = calc(sh_a, sh_min, minutes)

    boost = 1 + (minutes / 10) * 0.15

    if name in ["Shots", "Shots on Target"]:
        lh *= boost
        la *= boost

    if start_min >= 75 and name not in ["Cards", "Offsides", "Fouls"]:
        f = (start_min - 75) / 15

        if name == "Shots":
            lh *= 1 + f * 0.30
            la *= 1 + f * 0.30
        elif name == "Shots on Target":
            lh *= 1 + f * 0.22
            la *= 1 + f * 0.22
        elif name == "Corners":
            lh *= 1 + f * 0.25
            la *= 1 + f * 0.25

    total_before = lh + la

    lh, la = apply(name, lh, la)

    normalize = False

    if gap == "balanced":
        normalize = False
    elif name in ["Shots on Target", "Corners"]:
        normalize = True
    elif name == "Throw-ins":
        normalize = False
    elif name == "Shots" and gap != "strong":
        normalize = True

    if normalize:
        new = lh + la
        if new > 0:
            scale = total_before / new
            lh *= scale
            la *= scale

    ph = prob(lh)
    pa = prob(la)
    pt = prob(lh + la)

    st.markdown(f"### {name}")
    st.write(f"Home → {round(ph*100,1)}% | Odds: {round(odds(ph),2)}")
    st.write(f"Away → {round(pa*100,1)}% | Odds: {round(odds(pa),2)}")
    st.write(f"Total → {round(pt*100,1)}% | Odds: {round(odds(pt),2)}")
    st.markdown("---")
